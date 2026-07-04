"""Headless runners — drive the student (autocode) and teacher (puku-cli).

This is the seam where the teacher-student loop touches real processes. Both
agents run **through the local LiteLLM gateway** (OpenAI-compatible, default
``http://localhost:4000/v1``) so "teacher mode end to end" works with local
models — exactly the path the benchmarks and harness-tester rigs already use:

* **student** — ``autocode exec "<prompt>" --json --permission-mode bypassPermissions``
  with ``AUTOCODE_LLM_*`` pointed at the gateway; emits Tier-4.4 NDJSON.
* **teacher** — ``puku-cli --print --output-format stream-json --provider openai
  --model <alias> ...`` with ``OPENAI_BASE_URL`` pointed at the gateway and all
  ``ANTHROPIC_*`` vars cleared (so a misconfig cannot bill a real cloud key);
  emits Claude-Code-style stream-json. The prompt is fed on **stdin** because
  ``--add-dir`` is variadic and would otherwise swallow a positional prompt.

The command/env *builders* are pure functions (unit-tested); the subprocess runs
are thin wrappers exercised by the integration e2e. The playbook is loaded into
the student via ``--append-system-prompt`` (the online durable-memory path).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from autocode.anvil.teacher.recorder import from_autocode_ndjson, from_puku_stream
from autocode.anvil.teacher.schemas import ModelInfo, Task, Trajectory


@dataclass
class GatewayConfig:
    """Where both agents send their LLM traffic (the local gateway by default)."""

    api_base: str = ""
    api_key: str = ""
    student_model: str = ""
    teacher_model: str = ""
    student_bin: str = ""
    puku_bin: str = ""
    max_budget_usd: float = 0.50

    @classmethod
    def from_env(cls) -> GatewayConfig:
        return cls(
            api_base=os.environ.get("AUTOCODE_LLM_API_BASE", "http://localhost:4000/v1"),
            api_key=(
                os.environ.get("OPENROUTER_API_KEY")
                or os.environ.get("LITELLM_MASTER_KEY")
                or os.environ.get("LITELLM_API_KEY")
                or "sk-x"
            ),
            student_model=os.environ.get("AUTOCODE_BENCH_MODEL")
            or os.environ.get("AUTOCODE_LLM_MODEL")
            or "coding",
            teacher_model=os.environ.get("AUTOCODE_BENCH_PUKU_MODEL", "coding"),
            student_bin=os.environ.get("AUTOCODE_UNDER_TEST", "")
            or (shutil.which("autocode") or "autocode"),
            puku_bin=os.environ.get("PUKU_CLI_BIN", "") or (shutil.which("puku-cli") or "puku-cli"),
            max_budget_usd=float(os.environ.get("ANVIL_MAX_BUDGET_USD", "0.50")),
        )

    def is_local(self) -> bool:
        base = self.api_base.lower()
        return "localhost" in base or "127.0.0.1" in base or "0.0.0.0" in base


@dataclass
class RunResult:
    role: str
    trajectory: Trajectory
    diff: str
    exit_code: int
    raw_output: str = ""
    stderr: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


# --------------------------------------------------------------------------- #
# Pure command / env builders                                                   #
# --------------------------------------------------------------------------- #


def build_student_cmd(
    prompt: str,
    cfg: GatewayConfig,
    *,
    append_system_prompt: str = "",
) -> list[str]:
    cmd = [
        cfg.student_bin or "autocode",
        "exec",
        prompt,
        "--json",
        "--permission-mode",
        "bypassPermissions",
        "--max-budget-usd",
        str(cfg.max_budget_usd),
    ]
    if append_system_prompt.strip():
        cmd += ["--append-system-prompt", append_system_prompt]
    return cmd


def build_student_env(cfg: GatewayConfig, sandbox: Path) -> dict[str, str]:
    env = dict(os.environ)
    env["AUTOCODE_LLM_PROVIDER"] = "openrouter"
    env["AUTOCODE_LLM_API_BASE"] = cfg.api_base
    env["AUTOCODE_LLM_MODEL"] = cfg.student_model
    env["OPENROUTER_API_KEY"] = cfg.api_key
    env["OPENROUTER_MODEL"] = cfg.student_model
    env["AUTOCODE_SANDBOX"] = str(sandbox)
    return env


def build_teacher_cmd(cfg: GatewayConfig, sandbox: Path) -> list[str]:
    return [
        cfg.puku_bin or "puku-cli",
        "--print",
        "--verbose",
        "--output-format",
        "stream-json",
        "--provider",
        "openai",
        "--model",
        cfg.teacher_model,
        "--permission-mode",
        "bypassPermissions",
        "--max-budget-usd",
        str(cfg.max_budget_usd),
        "--add-dir",
        str(sandbox),
    ]


def build_teacher_env(cfg: GatewayConfig) -> dict[str, str]:
    env = dict(os.environ)
    env["OPENAI_BASE_URL"] = cfg.api_base
    env["OPENAI_API_KEY"] = cfg.api_key
    # Clear cloud keys so a misconfig can never bill a real provider.
    for k in ("ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL", "ANTHROPIC_AUTH_TOKEN"):
        env.pop(k, None)
    return env


# --------------------------------------------------------------------------- #
# Sandbox / git helpers                                                         #
# --------------------------------------------------------------------------- #


def prepare_sandbox(sandbox: str | Path) -> Path:
    """Make ``sandbox`` a git repo with a baseline commit so diffs are computable."""
    path = Path(sandbox)
    path.mkdir(parents=True, exist_ok=True)
    if not (path / ".git").is_dir():
        _git(["init", "-q"], path)
        _git(["config", "user.email", "anvil@local"], path)
        _git(["config", "user.name", "anvil"], path)
    _git(["add", "-A"], path)
    # Allow an empty baseline commit (greenfield tasks have no files yet).
    _git(["commit", "-q", "--allow-empty", "-m", "anvil baseline"], path)
    return path


def working_diff(sandbox: str | Path) -> str:
    path = Path(sandbox)
    _git(["add", "-A"], path)
    rc, out = _git(["diff", "--no-ext-diff", "--cached", "HEAD"], path, check=False)
    return out


def _git(args: list[str], cwd: Path, *, check: bool = True) -> tuple[int, str]:
    proc = subprocess.run(  # noqa: S603 - fixed launcher
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )
    if check and proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.returncode, (proc.stdout or "")


# --------------------------------------------------------------------------- #
# Thin subprocess wrappers                                                      #
# --------------------------------------------------------------------------- #


def run_student(
    prompt: str,
    sandbox: str | Path,
    cfg: GatewayConfig | None = None,
    *,
    trajectory_id: str = "tj_student",
    task: Task | None = None,
    append_system_prompt: str = "",
    timeout: int = 600,
) -> RunResult:
    cfg = cfg or GatewayConfig.from_env()
    sandbox = Path(sandbox)
    cmd = build_student_cmd(prompt, cfg, append_system_prompt=append_system_prompt)
    env = build_student_env(cfg, sandbox)
    started = time.monotonic()
    proc = subprocess.run(  # noqa: S603
        cmd, cwd=str(sandbox), env=env, capture_output=True, text=True, timeout=timeout
    )
    wall = time.monotonic() - started
    diff = working_diff(sandbox)
    tj = from_autocode_ndjson(
        proc.stdout,
        trajectory_id=trajectory_id,
        task=task or Task(instruction=prompt, repo=str(sandbox)),
        model=ModelInfo(alias=cfg.student_model, provider="openai", is_local=cfg.is_local()),
        final_diff=diff or None,
        wall_s=wall,
    )
    return RunResult(
        role="student",
        trajectory=tj,
        diff=diff,
        exit_code=proc.returncode,
        raw_output=proc.stdout,
        stderr=proc.stderr,
    )


def run_teacher(
    prompt: str,
    sandbox: str | Path,
    cfg: GatewayConfig | None = None,
    *,
    trajectory_id: str = "tj_teacher",
    task: Task | None = None,
    timeout: int = 600,
) -> RunResult:
    cfg = cfg or GatewayConfig.from_env()
    sandbox = Path(sandbox)
    cmd = build_teacher_cmd(cfg, sandbox)
    env = build_teacher_env(cfg)
    proc = subprocess.run(  # noqa: S603
        cmd,
        cwd=str(sandbox),
        env=env,
        input=prompt,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    diff = working_diff(sandbox)
    tj = from_puku_stream(
        proc.stdout,
        trajectory_id=trajectory_id,
        task=task or Task(instruction=prompt, repo=str(sandbox)),
        model=ModelInfo(alias=cfg.teacher_model, provider="openai", is_local=cfg.is_local()),
        final_diff=diff or None,
    )
    return RunResult(
        role="teacher",
        trajectory=tj,
        diff=diff,
        exit_code=proc.returncode,
        raw_output=proc.stdout,
        stderr=proc.stderr,
    )


__all__ = [
    "GatewayConfig",
    "RunResult",
    "build_student_cmd",
    "build_student_env",
    "build_teacher_cmd",
    "build_teacher_env",
    "prepare_sandbox",
    "working_diff",
    "run_student",
    "run_teacher",
]
