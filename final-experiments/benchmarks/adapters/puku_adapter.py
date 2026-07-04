"""puku-cli agent adapter — runs benchmark tasks through the puku-cli coding agent.

puku-cli (``@puku/puku-cli``) is a mature, Claude-Code-compatible CLI. In this harness it
serves as a **known-good control agent**: a trusted agent should solve solvable tasks, so
any failure it hits is evidence of a *harness* defect rather than an agent defect. That is
what makes it useful for calibrating the harness before trusting its verdicts on AutoCode.

Execution path (decided 2026-06-21): puku-cli is driven through the local LiteLLM gateway
(OpenAI-compatible) via gateway aliases, so calibration runs are free and match AutoCode's
own gateway path — no paid Anthropic usage.

Key behaviours that the calibration depends on (see
``docs/superpowers/specs/2026-06-21-harness-calibration-puku-design.md`` §5.6):

* The subprocess MUST run with ``cwd=sandbox`` — puku writes files into its CWD, so a
  missing ``cwd`` leaks artifacts into the repo (observed in the live smoke).
* puku self-reports ``tokens=0`` / ``cost=0`` through the OpenAI-provider gateway path even
  though the gateway itself meters usage. We therefore record what is reliable from puku's
  JSON (``num_turns``, ``duration_ms``, ``result``, ``stop_reason``, ``permission_denials``)
  and treat tokens/cost as gateway-sourced-or-unavailable, never a fabricated ``0``.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

# Add superproject root + autocode/src so we can reuse the shared gateway auth helper.
_BENCHMARKS_ROOT = Path(__file__).resolve().parent.parent
_SUPERPROJECT_ROOT = _BENCHMARKS_ROOT.parent
if str(_SUPERPROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_SUPERPROJECT_ROOT))
if str(_SUPERPROJECT_ROOT / "autocode" / "src") not in sys.path:
    sys.path.insert(0, str(_SUPERPROJECT_ROOT / "autocode" / "src"))

from benchmarks.docker_helpers import docker_exec as _docker_exec  # noqa: E402

from .base import (  # noqa: E402
    AgentResult,
    BenchmarkTask,
    BudgetProfile,
    ProviderHealthError,
)

# Gateway aliases are the only models we route puku through; they are free by policy.
GATEWAY_ALIASES: frozenset[str] = frozenset({
    "default", "tools", "tools_stable", "tools_large",
    "tools_stable_cloud", "tools_cloud", "tools_local",
    "bench", "bench_stable", "bench_large",
    "bench_stable_cloud", "bench_cloud",
    "swebench", "swebench_cloud",
    "coding", "coding_cloud",
    "thinking", "thinking_cloud",
    "default_cloud", "vision",
    "fast", "big", "local",
    "terminal_bench",
})

_DEFAULT_GATEWAY_BASE = "http://localhost:4000/v1"
_DEFAULT_MODEL = "coding"


class PukuAdapter:
    """Runs benchmark tasks through puku-cli, routed at the local gateway."""

    def __init__(self, model: str = ""):
        self._model = (
            model
            or os.environ.get("AUTOCODE_BENCH_PUKU_MODEL", "")
            or _DEFAULT_MODEL
        )
        # USD safety cap — gateway routes are free (cost 0), but the cap protects against
        # an accidental real-provider run. Only applies with --print.
        self._max_usd = os.environ.get("AUTOCODE_BENCH_PUKU_MAX_USD", "2.0")
        self._healthcheck_done = False
        self._healthcheck_error: str | None = None

    # --- AgentAdapter protocol -------------------------------------------------

    @property
    def name(self) -> str:
        return "puku"

    @property
    def version(self) -> str:
        exe = shutil.which("puku-cli")
        if exe:
            try:
                proc = subprocess.run(
                    ["puku-cli", "--version"],
                    capture_output=True, text=True, timeout=10,
                )
                return proc.stdout.strip() or "unknown"
            except Exception:
                pass
        return "unknown"

    @property
    def provider_mode(self) -> str:
        # Gateway aliases are free by policy; anything else is treated as paid.
        return "local_free" if self._model in GATEWAY_ALIASES else "paid_metered"

    @property
    def model(self) -> str:
        return self._model

    def pre_task_healthcheck(self) -> None:
        """Probe the gateway alias once so infra failures stop fast and classify cleanly."""
        if self._healthcheck_done:
            if self._healthcheck_error:
                raise ProviderHealthError(self._healthcheck_error)
            return
        try:
            self._probe_gateway_alias()
        except Exception as exc:
            self._healthcheck_error = str(exc)
            self._healthcheck_done = True
            raise ProviderHealthError(self._healthcheck_error) from exc
        self._healthcheck_done = True

    # --- Internals -------------------------------------------------------------

    def _gateway_base(self) -> str:
        return (
            os.environ.get("AUTOCODE_LLM_API_BASE", "").rstrip("/")
            or _DEFAULT_GATEWAY_BASE
        )

    def _gateway_key(self) -> str:
        try:
            from autocode.gateway_auth import get_gateway_api_key
            return get_gateway_api_key()
        except Exception:
            for name in ("LITELLM_API_KEY", "LITELLM_MASTER_KEY", "OPENROUTER_API_KEY"):
                val = os.environ.get(name, "").strip()
                if val:
                    return val
            return ""

    def _probe_gateway_alias(self) -> None:
        if self._model not in GATEWAY_ALIASES:
            return  # paid/native path — no harness preflight
        api_base = self._gateway_base()
        if not api_base.startswith(("http://", "https://")):
            return
        try:
            from autocode.gateway_auth import build_gateway_headers
            headers = build_gateway_headers({"Content-Type": "application/json"})
        except Exception:
            key = self._gateway_key()
            headers = {"Content-Type": "application/json", "Accept": "application/json"}
            if key:
                headers["Authorization"] = f"Bearer {key}"

        payload = json.dumps({
            "model": self._model,
            "messages": [{"role": "user", "content": "ok"}],
            "max_tokens": 1,
            "stream": False,
        }).encode("utf-8")
        request = Request(f"{api_base}/chat/completions", data=payload, headers=headers)
        try:
            with urlopen(request, timeout=15) as response:  # noqa: S310
                parsed = json.loads(response.read().decode("utf-8", errors="replace"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:200]
            raise RuntimeError(
                f"puku gateway alias '{self._model}' rejected at {api_base}: "
                f"HTTP {exc.code} {detail}"
            ) from exc
        except Exception as exc:
            raise RuntimeError(
                f"puku gateway alias '{self._model}' probe failed at {api_base}: {exc}"
            ) from exc
        if "choices" not in parsed:
            raise RuntimeError(
                f"puku gateway alias '{self._model}' probe returned no choices at {api_base}"
            )

    def _build_env(self) -> dict[str, str]:
        """Environment that routes puku-cli's OpenAI provider at the local gateway.

        ANTHROPIC_* are cleared so a misconfiguration can never silently bill the real
        Anthropic API instead of using the free gateway route.
        """
        env = os.environ.copy()
        env["OPENAI_BASE_URL"] = self._gateway_base()
        key = self._gateway_key()
        if key:
            env["OPENAI_API_KEY"] = key
        for var in ("ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL", "ANTHROPIC_AUTH_TOKEN"):
            env.pop(var, None)
        return env

    def _build_prompt(self, task: BenchmarkTask, work_dir: Path) -> str:
        task_md = ""
        task_md_path = work_dir / "task.md"
        if task_md_path.is_file():
            try:
                task_md = task_md_path.read_text(encoding="utf-8")[:3000]
            except Exception:
                task_md = ""
        parts = [
            f"You are a coding agent working in: {work_dir}",
            "",
            "TASK:",
            task.description or "(see task.md)",
        ]
        if task_md:
            parts += ["", "TASK DETAILS:", task_md]
        parts += [
            "",
            "RULES:",
            "- Make the changes needed to satisfy the task, then stop.",
            "- Do NOT modify test files; fix the source/implementation only.",
            "- Make the minimum changes necessary.",
        ]
        if task.grading_command and not task.extra.get("_container_name"):
            parts += ["", f"VERIFY WITH: {task.grading_command}"]
        return "\n".join(parts)

    @staticmethod
    def _parse_result_json(stdout: str) -> dict[str, Any]:
        """Parse puku's --output-format json result object (last JSON object in stdout)."""
        stdout = stdout.strip()
        if not stdout:
            return {}
        # Fast path: whole stdout is the object.
        try:
            obj = json.loads(stdout)
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass
        # Fallback: scan lines for the final JSON object (stream-json tails with result).
        for line in reversed(stdout.splitlines()):
            line = line.strip()
            if line.startswith("{") and line.endswith("}"):
                try:
                    obj = json.loads(line)
                    if isinstance(obj, dict) and obj.get("type") == "result":
                        return obj
                except Exception:
                    continue
        return {}

    @staticmethod
    def _git_create_baseline(work_dir: Path) -> None:
        """Commit a git baseline of the (failing) post-setup state.

        Many lanes grade with ``git show HEAD:<file>`` to enforce "only X changed" or
        "minimal diff". External-CLI agents leave no baseline, so those checks fail even on
        a correct fix (observed on B27). The AutoCode adapter does this internally; we
        mirror it so puku grades correctly on diff-based lanes. For fixture tasks that ship
        their own repo, ``git init`` is skipped and we just add a baseline commit on top,
        matching AutoCode's behaviour.
        """
        try:
            if not (work_dir / ".git").exists():
                subprocess.run(
                    "git init && git config user.email bench@test "
                    "&& git config user.name Bench",
                    shell=True, cwd=str(work_dir),
                    capture_output=True, text=True, timeout=30,
                )
            else:
                subprocess.run(
                    "git config user.email bench@test && git config user.name Bench",
                    shell=True, cwd=str(work_dir),
                    capture_output=True, text=True, timeout=10,
                )
            subprocess.run(
                "git add -A && git commit -m benchmark-baseline --allow-empty --no-verify",
                shell=True, cwd=str(work_dir),
                capture_output=True, text=True, timeout=30,
            )
        except Exception:
            pass

    def _run_grading(
        self, sandbox: Path, task: BenchmarkTask, env: dict[str, str],
    ) -> tuple[int, str]:
        container = task.extra.get("_container_name")
        if container:
            res = _docker_exec(container, task.grading_command, timeout=120)
            return res.returncode, (res.stdout + res.stderr)
        res = subprocess.run(
            task.grading_command,
            shell=True, cwd=str(sandbox), env=env,
            capture_output=True, text=True, timeout=120,
        )
        return res.returncode, ((res.stdout or "") + (res.stderr or ""))

    async def solve_task(
        self,
        task: BenchmarkTask,
        sandbox: Path,
        budget: BudgetProfile,
    ) -> AgentResult:
        start = time.monotonic()
        error = ""
        output = ""
        resolved = False
        puku_json: dict[str, Any] = {}

        puku_exe = shutil.which("puku-cli")
        if not puku_exe:
            return AgentResult(
                task_id=task.task_id,
                resolved=False,
                error="puku-cli not found on PATH",
                artifacts={"failure_type": "INFRA_FAIL"},
            )

        # Fixture tasks: sandbox IS the work dir; otherwise descend into a single repo.
        work_dir = sandbox
        if not task.extra.get("fixture_dir"):
            repo_name = task.extra.get("repo_name", "")
            if repo_name and (sandbox / repo_name).is_dir():
                work_dir = sandbox / repo_name

        # Establish a git baseline of the failing post-setup state so diff-based grading
        # (git show HEAD:...) works. Skipped for Docker lanes where grading runs in the
        # container against the mounted /work — the host baseline is still visible there.
        self._git_create_baseline(work_dir)

        env = self._build_env()
        prompt = self._build_prompt(task, work_dir)
        cmd = [
            puku_exe,
            "-p",
            "--output-format", "json",
            "--provider", "openai",
            "--model", self._model,
            "--permission-mode", "bypassPermissions",
            "--max-budget-usd", str(self._max_usd),
            prompt,
        ]

        try:
            proc = subprocess.run(
                cmd,
                cwd=str(work_dir),          # CRITICAL: confine puku to the sandbox
                env=env,
                capture_output=True,
                text=True,
                timeout=budget.wall_time_s,
                stdin=subprocess.DEVNULL,
            )
            puku_json = self._parse_result_json(proc.stdout)
            output = (puku_json.get("result") or proc.stdout)[:2000]
            if proc.returncode != 0 and not puku_json:
                error = (proc.stderr or "")[:1000]
            if puku_json.get("is_error"):
                subtype = str(puku_json.get("subtype") or "")
                if subtype and subtype != "success":
                    # A genuine puku run error (e.g. error_max_turns, error_during_execution).
                    error = error or f"puku run error: {subtype}"
                else:
                    # is_error with a 'success' subtype is a contradictory/aborted result —
                    # in practice an incomplete run, typically when the gateway is slow under
                    # load (observed at ~300s on the heavy sweep lanes). Treat as transient.
                    error = error or "puku aborted (incomplete run; likely gateway latency)"

            if task.grading_command:
                rc, grading_output = self._run_grading(sandbox, task, env)
                resolved = rc == 0
                if not resolved:
                    output += (
                        f"\n--- Grading ---\nExit code: {rc}\n"
                        f"{grading_output[:800]}"
                    )
            else:
                resolved = proc.returncode == 0 and not puku_json.get("is_error")
        except subprocess.TimeoutExpired:
            error = f"Timeout after {budget.wall_time_s}s"
        except Exception as e:  # noqa: BLE001
            error = f"{type(e).__name__}: {e}"

        elapsed = time.monotonic() - start

        # Failure classification consistent with benchmark_runner expectations.
        #   - no error, grading ran and failed  -> WRONG_FIX (a genuine agent miss)
        #   - timeout / puku abort / transport   -> INFRA_FAIL (transient; re-runnable)
        # The distinction matters: INFRA_FAIL is excluded from agent-capability scoring and
        # is a re-run candidate, whereas WRONG_FIX counts against the agent.
        failure_type = "RESOLVED" if resolved else "UNKNOWN"
        if not resolved:
            if not error:
                failure_type = "WRONG_FIX"
            else:
                failure_type = "INFRA_FAIL"

        usage = puku_json.get("usage", {}) if isinstance(puku_json, dict) else {}
        artifacts: dict[str, Any] = {
            "failure_type": failure_type,
            "agent": "puku",
            "puku_model_alias": self._model,
            "puku_num_turns": puku_json.get("num_turns"),
            "puku_duration_ms": puku_json.get("duration_ms"),
            "puku_stop_reason": puku_json.get("stop_reason"),
            "puku_permission_denials": puku_json.get("permission_denials"),
            # NOTE: tokens/cost are gateway-sourced; puku self-reports 0 on this path.
            "puku_self_reported_cost_usd": puku_json.get("total_cost_usd"),
            "metrics_source": "gateway_required_for_tokens",
        }

        # num_turns is the closest reliable proxy puku exposes in result mode; record it
        # as tool_calls only when present, otherwise leave 0 (precise tool-call counting
        # would require --output-format stream-json).
        tool_calls = int(puku_json.get("num_turns") or 0)

        return AgentResult(
            task_id=task.task_id,
            resolved=resolved,
            score=1.0 if resolved else 0.0,
            wall_time_s=round(elapsed, 1),
            tool_calls=tool_calls,
            tokens_in=int(usage.get("input_tokens") or 0),
            tokens_out=int(usage.get("output_tokens") or 0),
            error=error,
            output=output,
            artifacts=artifacts,
        )
