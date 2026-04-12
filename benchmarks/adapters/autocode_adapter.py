"""AutoCode agent adapter — runs tasks through AutoCode's AgentLoop.

Uses Ollama (local, free) by default. No API cost.
Provider mode derived dynamically from provider + model.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

# Add superproject root to path for benchmarks and autocode imports
_BENCHMARKS_ROOT = Path(__file__).resolve().parent.parent
_SUPERPROJECT_ROOT = _BENCHMARKS_ROOT.parent
PROJECT_ROOT = _SUPERPROJECT_ROOT  # backward compat alias
if str(_SUPERPROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_SUPERPROJECT_ROOT))
if str(_SUPERPROJECT_ROOT / "autocode" / "src") not in sys.path:
    sys.path.insert(0, str(_SUPERPROJECT_ROOT / "autocode" / "src"))

from benchmarks.docker_helpers import docker_exec as _docker_exec  # noqa: E402

from .base import AgentResult, BenchmarkTask, BudgetProfile  # noqa: E402

# --- Retry loop constants ---
MAX_GRADE_ATTEMPTS = 3
MIN_ATTEMPT_BUDGET_S = 60

# --- Shell task categories (get sysadmin framing, not test-fixing) ---
SHELL_CATEGORIES: frozenset[str] = frozenset({
    "version_control", "permissions", "scripting",
    "package_management", "file_operations", "networking",
    "data_processing", "algorithmic",
})


# --- P2-A: Deterministic syntax gate ---

def _syntax_check_python(filepath: str) -> str | None:
    """Run py_compile on a Python file. Returns error string or None."""
    if not filepath.endswith(".py"):
        return None
    try:
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", filepath],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            err = (result.stderr or result.stdout).strip()
            return f"SYNTAX ERROR in {filepath}: {err}"
    except (subprocess.TimeoutExpired, OSError):
        pass
    return None


# --- Traceback frame extraction ---

def _extract_traceback_frames(output: str) -> list[str]:
    """Extract File/line/function from Python tracebacks.

    Returns deduplicated list of 'File "path", line N, in func' strings,
    filtered to exclude stdlib, site-packages, and test infrastructure.
    """
    import re
    frames: list[str] = []
    seen: set[tuple[str, str]] = set()
    skip_patterns = (
        "/site-packages/", "/lib/python", "/unittest/",
        "/multiprocessing/", "/pluggy/", "/_pytest/",
        "<frozen ", "/importlib/",
    )
    for m in re.finditer(
        r'File "([^"]+)", line (\d+), in (\w+)', output,
    ):
        path, line, func = m.group(1), m.group(2), m.group(3)
        if any(p in path for p in skip_patterns):
            continue
        key = (path, line)
        if key not in seen:
            seen.add(key)
            frames.append(f'File "{path}", line {line}, in {func}')
    return frames

# --- Provider classification ---

# Gateway model aliases — these are all free-tier routed by the gateway
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


def classify_provider_mode(provider: str, model: str) -> str:
    """Classify a provider+model pair into a cost mode.

    Returns 'local_free', or 'paid_metered'.  Fails closed to paid_metered
    for unknown providers so the runner can block them by policy.

    Gateway aliases are always local_free — the gateway is a black box
    that manages provider selection internally.
    """
    if model in GATEWAY_ALIASES:
        return "local_free"
    if provider == "ollama":
        return "local_free"
    if provider == "openrouter":
        return "local_free" if model.endswith(":free") else "paid_metered"
    return "paid_metered"  # fail closed


# --- Tool restriction ---
BASH_ONLY_TOOLS: frozenset[str] = frozenset({"run_command", "read_file"})
BENCHMARK_BOOKKEEPING_FILES: frozenset[str] = frozenset({
    ".benchmark-sessions.db",
    ".benchmark-sessions.db-shm",
    ".benchmark-sessions.db-wal",
})


class AutoCodeAdapter:
    """Runs benchmark tasks through AutoCode's AgentLoop or Orchestrator."""

    def __init__(self, model: str = ""):
        self._provider = os.environ.get(
            "AUTOCODE_LLM_PROVIDER", "ollama",
        )
        # Use orchestrator path when AUTOCODE_USE_ORCHESTRATOR=1
        self._use_orchestrator = os.environ.get("AUTOCODE_USE_ORCHESTRATOR", "") == "1"
        # Check generic alias first, then provider-specific vars
        self._model = (
            model
            or os.environ.get("AUTOCODE_MODEL", "")
            or (os.environ.get("OPENROUTER_MODEL", "") if self._provider == "openrouter" else "")
            or os.environ.get("OLLAMA_MODEL", "")
        )
        if not self._model:
            raise ValueError(
                "No model specified. Set --model, AUTOCODE_MODEL, OLLAMA_MODEL, or OPENROUTER_MODEL."
            )

    @property
    def name(self) -> str:
        return "autocode"

    @property
    def version(self) -> str:
        return "0.1.0"

    @property
    def provider_mode(self) -> str:
        return classify_provider_mode(self._provider, self._model)

    @property
    def model(self) -> str:
        return self._model

    def pre_task_healthcheck(self) -> None:
        """Check that the LLM provider is reachable before starting a task."""
        pass  # Gateway health is checked by run_all_benchmarks.sh

    def _find_work_dir(self, sandbox: Path, task: BenchmarkTask) -> Path:
        """Find the actual working directory for the agent.

        For SWE-bench tasks, the repo is cloned into sandbox/repo_name.
        For fixture-based tasks (fixture_dir set), use sandbox directly —
        the fixture may contain its own git repos with specific state
        (e.g. detached HEAD with uncommitted changes) that must not be
        touched by _git_create_baseline.
        For other tasks, use the sandbox directly.
        """
        # Fixture-based tasks: sandbox IS the work dir.
        # Do NOT descend into child git repos — they are part of
        # the task state that the agent must work with as-is.
        if task.extra.get("fixture_dir"):
            return sandbox

        repo_name = task.extra.get("repo_name", "")
        if repo_name:
            repo_dir = sandbox / repo_name
            if repo_dir.is_dir():
                return repo_dir
        # Fallback: look for any git repo in sandbox
        for child in sandbox.iterdir():
            if child.is_dir() and (child / ".git").exists():
                return child
        return sandbox

    def _determine_protected_paths(
        self,
        task: BenchmarkTask,
        changed_files: list[str],
        test_patch_files: list[str],
    ) -> set[str]:
        """Return paths that should be restored before grading.

        Most fixture tasks should not let the agent mutate tests just to pass
        the verifier. Some lanes intentionally require test-file edits, so they
        can opt out of the test-file auto-protection with
        ``allow_test_file_edits`` while still using explicit protected paths.
        """
        protected = set(test_patch_files or [])
        protected.update(task.extra.get("protected_paths", []))

        if protected:
            return protected

        if task.extra.get("allow_test_file_edits"):
            return set()

        return {
            f for f in changed_files
            if any(
                p in f for p in (
                    "test_", "_test.py", "tests/",
                    "conftest", "pytest",
                )
            )
        }

    def _run_grading_command(
        self,
        sandbox: Path,
        grading_command: str,
        *,
        container_name: str | None = None,
        timeout: int = 120,
    ) -> tuple[int, str]:
        """Execute the benchmark grading command in Docker or host mode."""
        if container_name:
            result = _docker_exec(
                container_name,
                grading_command,
                timeout=timeout,
            )
            output = result.stdout + result.stderr
            return result.returncode, output

        result = subprocess.run(
            grading_command,
            shell=True,
            cwd=str(sandbox),
            env=self._bench_env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = (result.stdout or "") + (result.stderr or "")
        return result.returncode, output

    def _normalize_shell_command(self, command: str) -> str:
        """Normalize shell command spacing/quoting for exact comparisons."""
        return " ".join(command.split())

    def _is_grading_command_invocation(
        self,
        command: str,
        grading_command: str,
        *,
        sandbox: Path,
        work_dir: Path,
    ) -> bool:
        """Return True when a shell tool invocation is the benchmark verifier."""
        normalized_command = self._normalize_shell_command(command)
        normalized_grading = self._normalize_shell_command(grading_command)

        if normalized_command == normalized_grading:
            return True

        prefixes = [
            f"cd {self._normalize_shell_command(str(sandbox))} && ",
            f"cd {self._normalize_shell_command(str(work_dir))} && ",
        ]
        return any(
            normalized_command == prefix + normalized_grading
            for prefix in prefixes
        )

    def _maybe_terminate_grading_command_result(
        self,
        command: str,
        output: str,
        grading_command: str,
        *,
        sandbox: Path,
        work_dir: Path,
    ) -> str:
        """Terminate the loop when run_command successfully runs grading."""
        if not self._is_grading_command_invocation(
            command,
            grading_command,
            sandbox=sandbox,
            work_dir=work_dir,
        ):
            return output

        if output.startswith("Error") or "[exit code " in output:
            return output

        from autocode.agent.loop import encode_tool_termination

        return encode_tool_termination(
            f"PASSED\n{output}",
            "Benchmark verification passed. Stop editing and report the fix briefly.",
        )

    async def solve_task(
        self,
        task: BenchmarkTask,
        sandbox: Path,
        budget: BudgetProfile,
    ) -> AgentResult:
        """Run AutoCode AgentLoop on the task with outer grading retry loop."""
        start = time.monotonic()
        tool_call_count = 0
        error = ""
        output = ""
        resolved = False
        grade_attempts: list[dict] = []
        enforced_policy: dict | None = None
        task_md_content = ""
        index_build_ms = 0
        syntax_gate_checks = 0
        syntax_gate_rejections = 0

        # Ensure venv bin is on PATH for grading subprocesses
        self._bench_env = os.environ.copy()
        venv_bin = str(PROJECT_ROOT / ".venv" / "bin")
        if venv_bin not in self._bench_env.get("PATH", ""):
            self._bench_env["PATH"] = (
                f"{venv_bin}:{self._bench_env.get('PATH', '')}"
            )

        try:
            from autocode.agent.approval import (
                ApprovalManager,
                ApprovalMode,
            )
            from autocode.agent.loop import AgentLoop, encode_tool_termination
            from autocode.agent.tools import (
                clear_code_index_cache,
                create_default_registry,
            )
            from autocode.config import ShellConfig, load_config
            from autocode.layer4.llm import create_provider
            from autocode.session.store import SessionStore

            # Clear search index cache to prevent cross-task contamination
            clear_code_index_cache()

            # Determine working directory
            work_dir = self._find_work_dir(sandbox, task)

            # P2-B: Index warmup — pre-build L2 index
            index_build_ms = 0
            try:
                from autocode.layer2.index import CodeIndex
                _idx_start = time.monotonic()
                idx = CodeIndex()
                idx.build(str(work_dir))
                index_build_ms = int(
                    (time.monotonic() - _idx_start) * 1000,
                )
            except Exception:
                pass  # Non-critical — search_code works via BM25

            # P2-A: Syntax gate telemetry
            syntax_gate_checks = 0
            syntax_gate_rejections = 0

            # Load config, override for benchmark
            config = load_config(project_root=PROJECT_ROOT)
            config.llm.model = self._model
            config.llm.provider = self._provider
            # Gateway-first: use AUTOCODE_LLM_API_BASE if set
            gateway_base = os.environ.get("AUTOCODE_LLM_API_BASE", "")
            if gateway_base:
                config.llm.api_base = gateway_base
            elif self._provider == "openrouter":
                config.llm.api_base = "https://openrouter.ai/api/v1"
            else:
                config.llm.api_base = os.environ.get(
                    "OLLAMA_HOST", "http://localhost:11434",
                )
            config.shell.enabled = True
            config.shell.timeout = 120
            config.shell.max_timeout = 300
            config.shell.allow_network = True
            config.tui.approval_mode = "auto"
            config.llm.temperature = 0.7  # Higher temp for retry diversity

            # Set max iterations from budget
            original_max = AgentLoop.MAX_ITERATIONS
            AgentLoop.MAX_ITERATIONS = budget.max_tool_calls

            # Change CWD to working directory
            original_cwd = os.getcwd()
            os.chdir(work_dir)

            try:
                provider = create_provider(config)
                registry = create_default_registry(
                    project_root=str(work_dir),
                )

                # Register run_tests tool for any benchmark with grading
                _container_name = task.extra.get("_container_name")
                if task.grading_command:
                    from autocode.agent.tools import ToolDefinition

                    _sandbox_for_closure = sandbox
                    _cname_for_closure = _container_name
                    _gcmd_for_closure = task.grading_command

                    def _handle_run_tests(**_kwargs: Any) -> str:
                        """Run the grading command and terminate on success."""
                        try:
                            returncode, output = self._run_grading_command(
                                _sandbox_for_closure,
                                _gcmd_for_closure,
                                container_name=_cname_for_closure,
                                timeout=120,
                            )
                            # Truncate to last 2000 chars
                            if len(output) > 2000:
                                output = "...(truncated)\n" + output[-2000:]
                            if returncode == 0:
                                display = f"PASSED\n{output}"
                                return encode_tool_termination(
                                    display,
                                    "Benchmark verification passed. Stop editing and report the fix briefly.",
                                )
                            return f"FAILED (exit code {returncode})\n{output}"
                        except Exception as e:
                            return f"Error running tests: {e}"

                    registry.register(ToolDefinition(
                        name="run_tests",
                        description=(
                            "Run the test suite to verify your fix. "
                            "Returns PASSED or FAILED with test output."
                        ),
                        parameters={
                            "type": "object",
                            "properties": {},
                            "required": [],
                        },
                        handler=_handle_run_tests,
                        requires_approval=False,
                    ))

                    run_command_tool = registry.get("run_command")
                    if run_command_tool is not None:
                        _run_command_handler = run_command_tool.handler
                        _sandbox_for_command = sandbox
                        _work_dir_for_command = work_dir
                        _grading_command = task.grading_command

                        def _handle_run_command_with_grading(
                            command: str,
                            timeout: int = 30,
                        ) -> str:
                            output = _run_command_handler(
                                command=command,
                                timeout=timeout,
                            )
                            return self._maybe_terminate_grading_command_result(
                                command,
                                output,
                                _grading_command,
                                sandbox=_sandbox_for_command,
                                work_dir=_work_dir_for_command,
                            )

                        registry.register(ToolDefinition(
                            name=run_command_tool.name,
                            description=run_command_tool.description,
                            parameters=run_command_tool.parameters,
                            handler=_handle_run_command_with_grading,
                            requires_approval=run_command_tool.requires_approval,
                            mutates_fs=run_command_tool.mutates_fs,
                            executes_shell=run_command_tool.executes_shell,
                        ))

                # Enforce tool restriction (B8 bash-only lane)
                tool_restriction = task.extra.get("tool_restriction")
                enforced_policy = None
                if tool_restriction == "bash-only":
                    allowed = set(BASH_ONLY_TOOLS)
                    if task.grading_command:
                        allowed.add("run_tests")
                    allowed_frozen = frozenset(allowed)
                    registry = registry.filter(allowed_frozen)
                    enforced_policy = {
                        "tool_restriction": "bash-only",
                        "enforced": True,
                        "allowed_tools": sorted(allowed_frozen),
                    }
                shell_config = ShellConfig(
                    enabled=True,
                    timeout=120,
                    max_timeout=300,
                    allow_network=True,
                    allowed_commands=[
                        "npm", "npx", "node", "git", "mkdir",
                        "ls", "cat", "echo", "pytest", "python",
                        "pip", "uv", "ruff", "mypy", "make",
                        "python3", "pip3",
                    ],
                    blocked_commands=[
                        "rm -rf /", "rm -rf ~", "sudo",
                    ],
                )
                approval_mgr = ApprovalManager(
                    ApprovalMode.AUTO, shell_config,
                )
                db_path = sandbox / ".benchmark-sessions.db"
                session_store = SessionStore(db_path)
                session_id = session_store.create_session(
                    title=f"Benchmark: {task.task_id}",
                    model=config.llm.model,
                    provider=config.llm.provider,
                    project_dir=str(work_dir),
                )

                if self._use_orchestrator:
                    from autocode.agent.factory import create_orchestrator
                    orch, _stats = create_orchestrator(
                        provider=provider,
                        tool_registry=registry,
                        approval_manager=approval_mgr,
                        session_store=session_store,
                        session_id=session_id,
                    )
                    loop = orch.agent_loop
                else:
                    loop = AgentLoop(
                        provider=provider,
                        tool_registry=registry,
                        approval_manager=approval_mgr,
                        session_store=session_store,
                        session_id=session_id,
                    )

                # Track tool calls + tool-mix telemetry
                tool_mix: dict[str, int] = {}
                tool_call_errors: int = 0

                def on_tool_call(
                    name: str, status: str, result: str,
                ) -> None:
                    nonlocal tool_call_count, tool_call_errors
                    if status == "running":
                        tool_call_count += 1
                        tool_mix[name] = tool_mix.get(name, 0) + 1
                    elif status == "error":
                        tool_call_errors += 1

                async def approval_callback(
                    tool_name: str, arguments: dict,
                ) -> bool:
                    return True

                async def ask_user_callback(
                    question: str, options: list[str],
                    allow_text: bool,
                ) -> str:
                    if options:
                        return options[0]
                    return "Proceed with your best judgment."

                # Run initial test to capture error output for prompt
                initial_test_output = ""
                if task.grading_command:
                    try:
                        _init_rc, raw_output = self._run_grading_command(
                            sandbox,
                            task.grading_command,
                            container_name=task.extra.get("_container_name"),
                            timeout=120,
                        )
                        # Take last 1500 chars to keep prompt reasonable
                        if len(raw_output) > 1500:
                            initial_test_output = (
                                "...(truncated)\n" + raw_output[-1500:]
                            )
                        else:
                            initial_test_output = raw_output
                    except Exception:
                        pass  # Non-critical: agent can still run_tests

                # Read task.md if it exists in sandbox
                task_md_content = ""
                task_md_path = sandbox / "task.md"
                if task_md_path.is_file():
                    try:
                        task_md_content = task_md_path.read_text(
                            encoding="utf-8",
                        )[:3000]
                    except Exception:
                        pass

                # Build initial prompt (category-aware)
                prompt = self._build_prompt(
                    task,
                    initial_test_output=initial_test_output,
                    task_md=task_md_content,
                    work_dir_str=str(work_dir),
                )

                # P0-1: Snapshot test file paths for enforcement
                test_patch_files: list[str] = list(
                    task.extra.get("test_patch_files", []),
                )

                # P0-6: Create git baseline after test patch apply
                self._git_create_baseline(work_dir)

                # P0-4: Track previous attempt signatures
                prev_changed: set[str] | None = None
                stagnation_count = 0
                consecutive_zero_diffs = 0
                grading_signatures: list[str] = []

                # --- Outer grading retry loop ---
                for attempt in range(MAX_GRADE_ATTEMPTS):
                    elapsed_so_far = time.monotonic() - start
                    remaining = budget.wall_time_s - elapsed_so_far
                    if remaining < MIN_ATTEMPT_BUDGET_S:
                        break

                    # P0-6: Restore baseline before retries
                    # Skip for version_control tasks — their goal IS
                    # to change git state, restoring undoes the fix
                    if (
                        attempt > 0
                        and task.category not in ("version_control",)
                    ):
                        self._git_restore_baseline(work_dir)

                    result_text = await asyncio.wait_for(
                        loop.run(
                            prompt,
                            on_tool_call=on_tool_call,
                            approval_callback=approval_callback,
                            ask_user_callback=ask_user_callback,
                        ),
                        timeout=remaining,
                    )
                    output = result_text or ""

                    # P0-1 + P0-3: Detect changed files and
                    # test-file violations
                    changed_files = self._git_changed_files(work_dir)

                    protected = self._determine_protected_paths(
                        task,
                        changed_files,
                        test_patch_files,
                    )

                    test_files_changed = bool(
                        protected
                        and set(changed_files) & protected
                    )
                    protected_violation_files = (
                        list(set(changed_files) & protected)
                        if test_files_changed else []
                    )

                    # Restore protected files if agent edited them
                    if test_files_changed:
                        self._git_restore_files(
                            work_dir, list(protected),
                        )

                    # P0-3: Compute diff hash for stagnation
                    diff_output = self._git_diff_content(work_dir)
                    diff_hash = hashlib.md5(
                        diff_output.encode(),
                    ).hexdigest()[:8]

                    # Grade: run grading command if provided
                    # Use sandbox (not work_dir) because grading
                    # commands include `cd <repo> && ...`
                    if task.grading_command:
                        _cname = task.extra.get("_container_name")
                        # Version control tasks must grade on host
                        # because git state (branches, commits) isn't
                        # visible inside the Docker container
                        _grade_on_host = (
                            task.category == "version_control"
                        )
                        if _cname and not _grade_on_host:
                            grade_result = _docker_exec(
                                _cname,
                                task.grading_command,
                                timeout=120,
                            )
                        else:
                            grade_result = subprocess.run(
                                task.grading_command,
                                shell=True,
                                cwd=str(sandbox),
                                capture_output=True,
                                text=True,
                                timeout=120,
                                env=self._bench_env,
                            )
                        grading_output = (
                            grade_result.stdout + grade_result.stderr
                        )
                        resolved = grade_result.returncode == 0

                        # P0-3: Persist full grading output
                        grading_path = (
                            sandbox
                            / f"grading_attempt_{attempt + 1}.txt"
                        )
                        grading_path.write_text(
                            grading_output, encoding="utf-8",
                        )

                        # P0-3: Extended attempt telemetry
                        grade_attempts.append({
                            "attempt": attempt + 1,
                            "returncode": grade_result.returncode,
                            "resolved": resolved,
                            "elapsed_s": round(
                                time.monotonic() - start, 1,
                            ),
                            "changed_files": changed_files,
                            "test_files_changed": test_files_changed,
                            "protected_path_violation": protected_violation_files,
                            "diff_hash": diff_hash,
                            "grading_output_path": str(grading_path),
                            "tool_mix": dict(tool_mix),
                            "tool_call_errors": tool_call_errors,
                        })

                        # Reset per-attempt counters
                        tool_mix.clear()
                        tool_call_errors = 0

                        if resolved:
                            break

                        # Zero-diff tracking
                        if not changed_files:
                            consecutive_zero_diffs += 1
                        else:
                            consecutive_zero_diffs = 0

                        # Early-stop: 2 consecutive zero-diff attempts
                        if consecutive_zero_diffs >= 2:
                            output += (
                                "\n\n--- No Effective Edits ---\n"
                                "Agent produced ZERO file changes "
                                "on 2 consecutive attempts. "
                                "Stopping early."
                            )
                            break

                        # P0-4: Stagnation detection (diff-based)
                        current_changed = set(changed_files)
                        if (
                            prev_changed is not None
                            and current_changed == prev_changed
                        ):
                            stagnation_count += 1
                        else:
                            stagnation_count = 0
                        prev_changed = current_changed

                        if stagnation_count >= 2:
                            # Third repeat — early stop
                            output += (
                                "\n\n--- Stagnation ---\n"
                                "Same files changed 3 times "
                                "with no progress. Stopping."
                            )
                            break

                        # Grading signature stagnation detection
                        current_grading_sig = (
                            self._normalize_grading_signature(
                                grading_output,
                            )
                        )
                        grading_sig_repeated = (
                            len(grading_signatures) >= 1
                            and current_grading_sig
                            == grading_signatures[-1]
                        )
                        grading_signatures.append(current_grading_sig)

                        # P0-2: Structured failure feedback
                        prompt = self._build_feedback_prompt(
                            grading_output,
                            task.grading_command,
                            changed_files=changed_files,
                            test_files_changed=test_files_changed,
                            stagnation_count=stagnation_count,
                            consecutive_zero_diffs=consecutive_zero_diffs,
                            docker_grading=bool(
                                task.extra.get("_container_name"),
                            ),
                            test_patch=task.extra.get(
                                "test_patch", "",
                            ),
                            grading_signature_repeated=(
                                grading_sig_repeated
                            ),
                            prev_grading_signatures=grading_signatures,
                            protected_violation_files=protected_violation_files,
                        )
                    else:
                        # No grading command — single attempt only
                        break

                if not resolved and grade_attempts:
                    output += (
                        f"\n\n--- Grading ---\n"
                        f"Failed after {len(grade_attempts)} attempt(s)\n"
                        f"Last exit code: "
                        f"{grade_attempts[-1]['returncode']}"
                    )

                session_store.close()

            finally:
                os.chdir(original_cwd)
                AgentLoop.MAX_ITERATIONS = original_max

        except TimeoutError:
            error = f"Timeout after {budget.wall_time_s}s"
        except Exception as e:
            error = f"{type(e).__name__}: {e}"

        elapsed = time.monotonic() - start

        # Failure type classification
        failure_type = "RESOLVED" if resolved else "UNKNOWN"
        if not resolved:
            if error:
                if "XML" in error or "parse" in error.lower():
                    failure_type = "MODEL_XML_FAIL"
                else:
                    failure_type = "INFRA_FAIL"
            elif grade_attempts:
                all_zero_diff = all(
                    not a.get("changed_files") for a in grade_attempts
                )
                if all_zero_diff:
                    failure_type = "NO_EFFECTIVE_EDITS"
                else:
                    failure_type = "WRONG_FIX"

        artifacts: dict = {
            "grade_attempts": grade_attempts,
            "failure_type": failure_type,
            "harness_features": {
                "syntax_gate": False,
                "task_md_prompt": bool(task_md_content),
                "category_prompt": task.category in SHELL_CATEGORIES,
                "traceback_extraction": True,
                "index_warmup": index_build_ms > 0,
            },
            "index_build_ms": index_build_ms,
            "syntax_gate_checks": syntax_gate_checks,
            "syntax_gate_rejections": syntax_gate_rejections,
        }
        if enforced_policy is not None:
            artifacts["enforced_policy"] = enforced_policy

        return AgentResult(
            task_id=task.task_id,
            resolved=resolved,
            wall_time_s=round(elapsed, 1),
            tool_calls=tool_call_count,
            error=error,
            output=output[:2000],
            artifacts=artifacts,
        )

    def _build_prompt(
        self,
        task: BenchmarkTask,
        initial_test_output: str = "",
        task_md: str = "",
        work_dir_str: str = "",
    ) -> str:
        """Build the agent prompt from the task.

        Uses category-aware framing: shell tasks (git, permissions)
        get sysadmin framing; code tasks get test-fixing framing.
        Includes task.md content when available.
        """
        fail_tests = task.extra.get("FAIL_TO_PASS", [])
        test_list = (
            "\n".join(f"  - {t}" for t in fail_tests) if fail_tests else ""
        )
        docker_grading = bool(task.extra.get("_container_name"))
        is_shell_task = task.category in SHELL_CATEGORIES

        # Category-aware framing (driven by manifest metadata)
        if is_shell_task and task_md:
            # Shell/sysadmin task with task.md — use task.md as primary
            prompt = (
                f"You are a system administration agent.\n\n"
                f"WORKING DIRECTORY: {work_dir_str}\n\n"
                f"TASK:\n{task_md}\n\n"
                "RULES:\n"
                "- You MUST call tools to complete the task.\n"
                "- Use run_command to execute shell commands.\n"
                "- Use read_file to inspect files.\n"
                "- Complete ALL requirements listed in the task.\n"
                "- After each step, verify with run_command that it "
                "worked before moving on.\n"
                "- Do NOT modify any test files (test_*.py, *_test.py). "
                "Fix the SOURCE code only.\n"
                "- Make the MINIMUM changes needed. Do not rewrite "
                "entire files when a small edit will suffice.\n"
            )
            # Category-specific guidance
            if task.category == "version_control":
                prompt += (
                    "- IMPORTANT: Before finishing, you MUST verify:\n"
                    "  1. Run `git rev-parse --abbrev-ref HEAD` — "
                    "must show the target branch (NOT 'HEAD')\n"
                    "  2. Run `git status --porcelain` — must be empty\n"
                    "- If HEAD is detached, you MUST switch to the "
                    "target branch. Use `git stash --include-untracked` "
                    "first to save changes, then `git checkout <branch>`, "
                    "then `git stash pop`, then commit.\n"
                    "- Do NOT finish until branch state is correct.\n"
                )
            elif task.category == "permissions":
                prompt += (
                    "- For chmod tasks: note that DIRECTORIES and FILES "
                    "need DIFFERENT permissions. Read the requirements "
                    "carefully to distinguish directory permissions "
                    "from file permissions.\n"
                    "- Verify each permission with "
                    "`stat -c '%a %n' <path>` after setting it.\n"
                )
            if task.grading_command and not docker_grading:
                prompt += (
                    f"\nVERIFICATION COMMAND: {task.grading_command}\n"
                    "Run this after completing the task to verify.\n"
                )
            return prompt

        if task_md and not fail_tests:
            # Non-shell task with task.md but no failing tests
            # (e.g. algorithmic tasks like chess)
            prompt = (
                f"You are a coding agent.\n\n"
                f"WORKING DIRECTORY: {work_dir_str}\n\n"
                f"TASK:\n{task_md}\n\n"
                "RULES:\n"
                "- You MUST call tools to complete the task.\n"
                "- Use read_file, edit_file, write_file, and "
                "run_command as needed.\n"
                "- Do NOT modify any test files (test_*.py, *_test.py). "
                "Fix the SOURCE code only.\n"
                "- Make the MINIMUM changes needed.\n"
            )
            if task.grading_command and not docker_grading:
                prompt += (
                    f"\nVERIFICATION: {task.grading_command}\n"
                )
            return prompt

        # Standard code-fixing framing (SWE-bench style)
        prompt = (
            f"You are a coding agent working in a "
            f"{task.repo or 'Python'} repository.\n\n"
        )
        if work_dir_str:
            prompt += f"WORKING DIRECTORY: {work_dir_str}\n\n"
        prompt += (
            "IMPORTANT: The test patch has already been pre-applied. "
            "The failing tests are already in the codebase. "
            "You MUST fix the SOURCE CODE only — do NOT modify any test "
            "files.\n\n"
            f"BUG REPORT:\n{task.description}\n\n"
        )

        # Include task.md if available (additional context)
        if task_md:
            prompt += f"TASK DETAILS:\n{task_md}\n\n"

        if test_list:
            prompt += (
                f"FAILING TESTS (must pass after your fix):\n"
                f"{test_list}\n\n"
            )

        if task.grading_command and not docker_grading:
            prompt += (
                f"GRADING COMMAND (wrapped by run_tests):\n"
                f"  {task.grading_command}\n\n"
            )

        bash_only = task.extra.get("tool_restriction") == "bash-only"

        if docker_grading:
            # Docker tasks: agent can now self-verify via run_tests tool
            prompt += (
                "MANDATORY WORKFLOW — follow these steps exactly:\n"
                "Step 1: Read the failing test file(s) to understand what "
                "the tests expect.\n"
                "Step 2: Use read_file to read the SOURCE file(s) that "
                "need fixing (NOT the test files).\n"
                "Step 3: Understand what the tests expect and what the "
                "source code does wrong.\n"
            )
            if bash_only:
                prompt += (
                    "Step 4: Use run_command to make precise scripted "
                    "edits to the SOURCE code. Prefer `python - <<'PY'` "
                    "text-rewrite scripts for reliable search/replace. "
                    "Do NOT rewrite whole files unless the file is "
                    "tiny. Make the MINIMUM change needed.\n"
                    "Step 4b: Immediately verify the edit by running "
                    "`git diff -- <file>` or re-reading the edited "
                    "region before running tests.\n"
                )
            else:
                prompt += (
                    "Step 4: Use edit_file to fix the SOURCE code. "
                    "Make the MINIMUM change needed. Use edit_file "
                    "(NOT write_file) for editing existing files.\n"
                )
            prompt += (
                "Step 5: Use run_tests to verify your fix. If tests "
                "fail, read the error output, adjust your fix, and "
                "repeat from Step 4.\n\n"
                "RULES:\n"
                "- You MUST call tools. Do NOT just describe the fix.\n"
                "- Do NOT modify test files — they are already correct.\n"
                "- Fix the SOURCE code that the tests exercise.\n"
            )
            if bash_only:
                prompt += (
                    "- You only have run_command, read_file, and "
                    "run_tests available.\n"
                    "- Prefer `python - <<'PY'` for multi-line edits; "
                    "avoid brittle `sed -i` when the change spans "
                    "multiple tokens or lines.\n"
                    "- After every edit, inspect the diff before "
                    "re-running tests.\n"
                    "- Make one small change at a time, then verify.\n"
                )
            else:
                prompt += (
                    "- Use edit_file (NOT write_file) for editing "
                    "existing files.\n"
                )
            prompt += (
                "- If you receive feedback that tests failed, read the "
                "error output and adjust your fix.\n"
                "- When tests fail, examine the test file's imports and "
                "the test module name to identify which source files to "
                "investigate. Do not limit yourself to files you have "
                "already read."
            )
        elif bash_only:
            prompt += (
                "MANDATORY WORKFLOW — follow these steps exactly:\n"
                "Step 1: Use run_tests to see the current failures and "
                "read the output carefully.\n"
                "Step 2: Use read_file to read the SOURCE file(s) that "
                "need fixing (NOT the test files).\n"
                "Step 3: Understand what the tests expect and what the "
                "source code does wrong.\n"
                "Step 4: Use run_command to make precise scripted edits "
                "to the SOURCE code. Prefer `python - <<'PY'` "
                "text-rewrite scripts for reliable search/replace. "
                "Do NOT rewrite whole files unless the file is tiny. "
                "Make the MINIMUM change needed.\n"
                "Step 5: Immediately verify the edit by running "
                "`git diff -- <file>` or re-reading the edited "
                "region before running tests.\n"
                "Step 6: Use run_tests again to verify tests pass.\n"
                "Step 7: If tests still fail, read the error output, "
                "adjust your fix, and repeat from Step 4.\n\n"
                "RULES:\n"
                "- You MUST call tools. Do NOT just describe the fix.\n"
                "- Do NOT modify test files — they are already correct.\n"
                "- Fix the SOURCE code that the tests exercise.\n"
                "- You only have run_command and read_file available.\n"
                "- Prefer `python - <<'PY'` for multi-line edits; "
                "avoid brittle `sed -i` when the change spans "
                "multiple tokens or lines.\n"
                "- After every edit, inspect the diff before "
                "re-running tests.\n"
                "- Make one small change at a time, then verify.\n"
                "- After writing your fix, ALWAYS use run_tests to verify.\n"
                "- If tests fail, read the error output and iterate.\n"
                "- When tests fail, examine the test file's imports and "
                "the test module name to identify which source files to "
                "investigate. Do not limit yourself to files you have "
                "already read."
            )
        else:
            prompt += (
                "MANDATORY WORKFLOW — follow these steps exactly:\n"
                "Step 1: Use run_tests to see the current failures and "
                "read the output carefully.\n"
                "Step 2: Use read_file to read the SOURCE file(s) that "
                "need fixing (NOT the test files).\n"
                "Step 3: Understand what the tests expect and what the "
                "source code does wrong.\n"
                "Step 4: Use edit_file to fix the SOURCE code. Make the "
                "MINIMUM change needed. Use edit_file (NOT write_file) "
                "for editing existing files.\n"
                "Step 5: Use run_tests again to verify tests pass.\n"
                "Step 6: If tests still fail, read the error output, "
                "adjust your fix, and repeat from Step 4.\n\n"
                "RULES:\n"
                "- You MUST call tools. Do NOT just describe the fix.\n"
                "- Do NOT modify test files — they are already correct.\n"
                "- Fix the SOURCE code that the tests exercise.\n"
                "- Use edit_file (NOT write_file) for editing existing "
                "files.\n"
                "- After writing your fix, ALWAYS use run_tests to verify.\n"
                "- If tests fail, read the error output and iterate.\n"
                "- When tests fail, examine the test file's imports and "
                "the test module name to identify which source files to "
                "investigate. Do not limit yourself to files you have "
                "already read."
            )

        if initial_test_output:
            prompt += (
                "\n\nINITIAL TEST OUTPUT (current failures):\n"
                f"```\n{initial_test_output}\n```"
            )

        # Inject test patch so agent sees exactly what tests expect
        test_patch = task.extra.get("test_patch", "")
        if test_patch:
            # Truncate very large patches to keep prompt reasonable
            if len(test_patch) > 3000:
                test_patch = test_patch[:3000] + "\n...(truncated)"
            prompt += (
                "\n\nTEST PATCH (the failing test code — read this "
                "carefully to understand what the test expects):\n"
                f"```diff\n{test_patch}\n```"
            )

        return prompt

    @staticmethod
    def _parse_verifier_requirements(
        grading_output: str,
    ) -> tuple[list[str], list[str]]:
        """Parse PASS/FAIL requirement lines from verifier output.

        Returns (passed, failed) lists of requirement descriptions.
        """
        passed: list[str] = []
        failed: list[str] = []
        for line in grading_output.splitlines():
            stripped = line.strip()
            if stripped.startswith("PASS:"):
                passed.append(stripped)
            elif stripped.startswith("FAIL:"):
                failed.append(stripped)
        return passed, failed

    @staticmethod
    def _normalize_grading_signature(grading_output: str) -> str:
        """Extract a normalized failure signature for stagnation detection.

        Keeps only PASS/FAIL/FAILED/ERROR lines, sorted, to detect
        identical grading outcomes across retries.
        """
        sig_lines = []
        for line in grading_output.splitlines():
            stripped = line.strip()
            if any(
                stripped.startswith(pfx)
                for pfx in ("PASS:", "FAIL:", "FAILED ", "ERROR ")
            ):
                sig_lines.append(stripped)
        sig_lines.sort()
        return "\n".join(sig_lines)

    def _build_feedback_prompt(
        self,
        grading_output: str,
        grading_command: str,
        *,
        changed_files: list[str] | None = None,
        test_files_changed: bool = False,
        stagnation_count: int = 0,
        consecutive_zero_diffs: int = 0,
        docker_grading: bool = False,
        test_patch: str = "",
        grading_signature_repeated: bool = False,
        prev_grading_signatures: list[str] | None = None,
        protected_violation_files: list[str] | None = None,
    ) -> str:
        """Build a structured feedback prompt after a failed attempt.

        Order per Codex Entry 803:
        1. Unmet verifier requirements (FAIL lines)
        2. Last changed files + diff snippet
        3. Oscillation / repeat warning
        4. Targeted assertion/error fragments
        5. Raw tail as fallback context
        """
        parts: list[str] = []

        # --- 1. Unmet verifier requirements (FAIL lines first) ---
        v_passed, v_failed = self._parse_verifier_requirements(
            grading_output,
        )
        if v_failed or v_passed:
            total = len(v_passed) + len(v_failed)
            req_block = (
                f"REQUIREMENTS STATUS ({len(v_passed)}/{total} passing):\n"
            )
            for f in v_failed:
                req_block += f"  ✗ {f}  ← FOCUS HERE\n"
            for p in v_passed:
                req_block += f"  ✓ {p}\n"
            if v_failed:
                req_block += (
                    f"\n{len(v_failed)} requirement(s) still failing. "
                    "Focus ONLY on the failing ones."
                )
            parts.append(req_block)

        # Zero-diff hard warning
        if consecutive_zero_diffs >= 1:
            parts.append(
                "CRITICAL WARNING: Your previous attempt produced "
                "ZERO file edits. The grading tests CANNOT pass "
                "without source code modifications. You MUST use "
                "edit_file or write_file tools to modify the "
                "relevant source files. Do NOT just read and "
                "analyze — you must WRITE code changes."
            )

        # Protected-path violation warning (names exact files)
        if test_files_changed:
            violation_list = ", ".join(
                protected_violation_files[:5],
            ) if protected_violation_files else "test files"
            parts.append(
                f"CRITICAL: Your previous attempt edited PROTECTED "
                f"files: {violation_list}. Those edits have been "
                "REVERTED. You MUST NOT modify these files. "
                "Fix SOURCE code only — leave test files, config "
                "fixtures, and data files untouched."
            )

        # --- 2. Last changed files ---
        if changed_files:
            parts.append(
                "YOUR PREVIOUS CHANGES:\n"
                + "\n".join(f"  - {f}" for f in changed_files)
            )
        elif changed_files is not None:
            parts.append(
                "YOUR PREVIOUS CHANGES: NONE — you did not modify "
                "any files."
            )

        # --- 3. Oscillation / repeat / stagnation warnings ---
        if grading_signature_repeated:
            parts.append(
                "CRITICAL: Your last 2 attempts produced IDENTICAL "
                "grading results. Your current approach is NOT "
                "working. You MUST try something fundamentally "
                "different:\n"
                "- Re-read the failing requirement carefully\n"
                "- Look for files or commands you haven't tried\n"
                "- Consider a completely different strategy"
            )
        elif stagnation_count >= 1:
            parts.append(
                "WARNING: You are repeating the same fix. Try a "
                "DIFFERENT approach: read the failing test more "
                "carefully, look at related source files, or "
                "consider a different fix strategy."
            )

        # Oscillation detection: A→B→A pattern
        if prev_grading_signatures and len(prev_grading_signatures) >= 2:
            current_sig = self._normalize_grading_signature(grading_output)
            if (
                current_sig == prev_grading_signatures[-2]
                and current_sig != prev_grading_signatures[-1]
            ):
                parts.append(
                    "WARNING: You are oscillating between two "
                    "different failure states. Your fix attempt "
                    "reverted to an earlier error. Try a completely "
                    "new approach instead of alternating."
                )

        # --- 4. Targeted assertion/error fragments ---
        failing_tests = self._parse_failing_tests(grading_output)
        if failing_tests:
            parts.append(
                "FAILING TESTS:\n"
                + "\n".join(f"  - {t}" for t in failing_tests[:10])
            )

        assertions = self._parse_assertions(grading_output)
        if assertions:
            parts.append(
                "KEY ERRORS:\n"
                + "\n".join(f"  - {a}" for a in assertions[:5])
            )

        # Deterministic traceback frame extraction
        tb_frames = _extract_traceback_frames(grading_output)
        if tb_frames:
            parts.append(
                "TRACEBACK FRAMES (from test output):\n"
                + "\n".join(f"  {f}" for f in tb_frames[:10])
            )

        # Source discovery
        source_candidates = self._discover_source_candidates(
            grading_output, test_patch, failing_tests,
        )
        if source_candidates:
            parts.append(
                "SOURCE FILE CANDIDATES (investigate these):\n"
                + "\n".join(f"  - {s}" for s in source_candidates[:8])
            )

        # --- 5. Raw tail as fallback context ---
        max_tail = 1200
        tail = (
            grading_output[-max_tail:]
            if len(grading_output) > max_tail
            else grading_output
        )
        parts.append(f"Test output (tail):\n```\n{tail}\n```")

        if docker_grading:
            parts.append(
                "Fix the SOURCE code (not test files) to make the "
                "tests pass. The harness will re-run tests in the "
                "Docker container automatically after your fix."
            )
        else:
            parts.append(
                f"Grading command: {grading_command}\n\n"
                "Fix the SOURCE code (not test files) to make the "
                "tests pass. Run the grading command after your fix."
            )

        return "\n\n".join(parts)

    # --- P0-2: Grading output parsers ---

    @staticmethod
    def _parse_failing_tests(output: str) -> list[str]:
        """Extract failing test names from grading output."""
        tests: list[str] = []
        for line in output.splitlines():
            stripped = line.strip()
            if stripped.startswith(("FAILED ", "ERROR ")):
                tests.append(stripped)
            elif " FAILED" in stripped and "::" in stripped:
                tests.append(stripped)
        return tests

    @staticmethod
    def _parse_assertions(output: str) -> list[str]:
        """Extract assertion/error messages from grading output."""
        assertions: list[str] = []
        for line in output.splitlines():
            stripped = line.strip()
            if any(
                kw in stripped
                for kw in (
                    "AssertionError",
                    "assert ",
                    "Expected",
                    "expected",
                    "AttributeError",
                    "TypeError",
                    "ImportError",
                    "ModuleNotFoundError",
                    "NameError",
                    "ValueError",
                )
            ):
                if len(stripped) < 200:
                    assertions.append(stripped)
        return assertions

    # --- P0-3: Source file discovery ---

    @staticmethod
    def _extract_traceback_paths(output: str) -> list[str]:
        """Extract file paths from Python traceback lines."""
        import re
        paths: list[str] = []
        for m in re.finditer(r'File "([^"]+)", line \d+', output):
            path = m.group(1)
            # Skip standard library and site-packages
            if "/site-packages/" in path or "/lib/python" in path:
                continue
            paths.append(path)
        return paths

    @staticmethod
    def _extract_imports_from_patch(test_patch: str) -> list[str]:
        """Extract imported module names from a test patch diff."""
        import re
        modules: list[str] = []
        for line in test_patch.splitlines():
            # Only look at added lines in the diff
            if not line.startswith("+"):
                continue
            # from X.Y import Z
            m = re.match(r"\+\s*from\s+([\w.]+)\s+import", line)
            if m:
                modules.append(m.group(1))
                continue
            # import X.Y
            m = re.match(r"\+\s*import\s+([\w.]+)", line)
            if m:
                modules.append(m.group(1))
        return modules

    @staticmethod
    def _extract_diff_file_paths(test_patch: str) -> list[str]:
        """Extract file paths from diff headers in a test patch.

        Parses 'diff --git a/path b/path' and '--- a/path' / '+++ b/path'
        headers to find which test files were modified. Returns paths with
        the leading a/ or b/ stripped.
        """
        import re
        paths: list[str] = []
        seen: set[str] = set()
        for line in test_patch.splitlines():
            # diff --git a/testing/test_foo.py b/testing/test_foo.py
            m = re.match(r"diff --git a/(.+?) b/(.+)", line)
            if m:
                p = m.group(2)
                if p not in seen:
                    seen.add(p)
                    paths.append(p)
                continue
            # +++ b/testing/test_foo.py
            m = re.match(r"\+\+\+ b/(.+)", line)
            if m:
                p = m.group(1)
                if p not in seen:
                    seen.add(p)
                    paths.append(p)
        return paths

    @staticmethod
    def _test_path_to_source_candidates(test_path: str) -> list[str]:
        """Map a test file path to candidate source file paths.

        Given 'testing/test_unittest.py', produces candidates like:
        - src/_pytest/unittest.py (framework-internal pattern)
        - _pytest/unittest.py (package-internal pattern)
        - unittest.py (bare module)
        - src/unittest.py (src/ prefix)

        This handles projects like pytest where 'testing/test_X.py'
        corresponds to 'src/_pytest/X.py'.
        """
        parts = test_path.replace("\\", "/").rsplit("/", 1)
        basename = parts[-1]
        parent_dir = parts[0] if len(parts) > 1 else ""

        # Strip test_ prefix or _test suffix
        if basename.startswith("test_"):
            source_base = basename[5:]  # test_unittest.py -> unittest.py
        elif basename.endswith("_test.py"):
            source_base = basename[:-8] + ".py"
        else:
            return []

        source_stem = source_base.replace(".py", "")
        candidates: list[str] = []

        # Pattern 1: src/_<project>/X.py (pytest-style: testing/test_X -> src/_pytest/X)
        # Detect project name from parent dir pattern
        if parent_dir in ("testing", "tests", "test"):
            # Try common framework-internal patterns
            for prefix in ["src/_pytest", "_pytest", "src"]:
                candidates.append(f"{prefix}/{source_base}")

        # Pattern 2: direct source tree mirror
        # testing/test_foo.py -> src/foo.py, lib/foo.py, <pkg>/foo.py
        for prefix in ["src", "lib", ""]:
            path = f"{prefix}/{source_base}" if prefix else source_base
            if path not in candidates:
                candidates.append(path)

        # Pattern 3: nested package (e.g. mypackage/X.py)
        # Look for any directory matching the stem with _ prefix
        candidates.append(f"src/_{source_stem}/{source_stem}.py")

        return candidates

    @staticmethod
    def _test_name_to_source_hints(
        failing_tests: list[str],
    ) -> list[str]:
        """Map failing test file names to likely source module names.

        e.g. test_unittest.py -> unittest.py, test_aggregates.py ->
        aggregates.py
        """
        import re
        hints: list[str] = []
        seen: set[str] = set()
        for test_line in failing_tests:
            # Extract file part: FAILED testing/test_foo.py::TestBar
            m = re.search(r"([\w/\\]+\.py)", test_line)
            if not m:
                continue
            test_file = m.group(1).replace("\\", "/")
            basename = test_file.rsplit("/", 1)[-1]
            # Strip test_ prefix
            if basename.startswith("test_"):
                source_name = basename[5:]  # test_foo.py -> foo.py
            elif basename.endswith("_test.py"):
                source_name = basename[:-8] + ".py"
            else:
                continue
            if source_name not in seen:
                seen.add(source_name)
                hints.append(source_name)
        return hints

    def _discover_source_candidates(
        self,
        grading_output: str,
        test_patch: str,
        failing_tests: list[str],
    ) -> list[str]:
        """Combine multiple signals to suggest source files to investigate.

        Signals:
        1. Traceback paths (filtered to non-test files)
        2. Imports from test patch (added lines only)
        3. Test name -> source name heuristic
        4. Diff header file paths -> source path candidates
        """
        candidates: list[str] = []
        seen: set[str] = set()

        def _add(item: str) -> None:
            if item not in seen:
                seen.add(item)
                candidates.append(item)

        # Signal 1: traceback paths (non-test files)
        for path in self._extract_traceback_paths(grading_output):
            basename = path.rsplit("/", 1)[-1]
            is_test = (
                basename.startswith("test_")
                or basename.endswith("_test.py")
                or "/test_" in path
                or "/tests/" in path
                or "/testing/" in path
            )
            if not is_test:
                _add(path)

        # Signal 2: imports from test patch → module paths
        if test_patch:
            for mod in self._extract_imports_from_patch(test_patch):
                # Convert dotted module to path hint
                # e.g. _pytest.unittest -> _pytest/unittest.py
                path_hint = mod.replace(".", "/") + ".py"
                _add(f"(module) {path_hint}")

        # Signal 3: test name -> source name heuristic
        for hint in self._test_name_to_source_hints(failing_tests):
            _add(
                f"(search for) {hint} — likely source for "
                f"failing test"
            )

        # Signal 4: diff header paths -> source path candidates
        # Maps test file paths from the patch to likely source locations
        # e.g. testing/test_unittest.py -> src/_pytest/unittest.py
        if test_patch:
            for test_path in self._extract_diff_file_paths(test_patch):
                for src_candidate in self._test_path_to_source_candidates(
                    test_path,
                ):
                    _add(f"(source candidate) {src_candidate}")

        return candidates

    # --- P0-6: Git checkpoint helpers ---

    @staticmethod
    def _git_create_baseline(work_dir: Path) -> bool:
        """Create a git baseline commit after test patch apply.

        Returns True if baseline was created successfully.
        Raises RuntimeError if commit fails — all downstream
        enforcement depends on a valid baseline.

        If work_dir is not a git repo (e.g. fixture-based task sandbox),
        initialises one first so that retry-loop diffing still works.
        """
        try:
            # Init a git repo if one doesn't exist (fixture sandboxes)
            if not (work_dir / ".git").exists():
                init = subprocess.run(
                    "git init && git config user.email bench@test "
                    "&& git config user.name Bench",
                    shell=True, cwd=str(work_dir),
                    capture_output=True, text=True, timeout=30,
                )
                if init.returncode != 0:
                    raise RuntimeError(
                        f"Git init failed (rc={init.returncode})"
                        f": {init.stderr[:200]}"
                    )
            # Always set git config — Docker containers may lack identity
            subprocess.run(
                "git config user.email bench@test "
                "&& git config user.name Bench",
                shell=True, cwd=str(work_dir),
                capture_output=True, text=True, timeout=10,
            )
            proc = subprocess.run(
                "git add -A && git commit -m benchmark-baseline "
                "--allow-empty --no-verify",
                shell=True, cwd=str(work_dir),
                capture_output=True, text=True, timeout=30,
            )
            if proc.returncode != 0:
                raise RuntimeError(
                    f"Baseline commit failed (rc={proc.returncode})"
                    f": {proc.stderr[:200]}"
                )
            return True
        except subprocess.TimeoutExpired:
            raise RuntimeError("Baseline commit timed out")
        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(f"Baseline commit error: {e}")

    @staticmethod
    def _git_restore_baseline(work_dir: Path) -> None:
        """Restore working directory to baseline state."""
        try:
            subprocess.run(
                "git checkout -- .",
                shell=True, cwd=str(work_dir),
                capture_output=True, text=True, timeout=30,
            )
            subprocess.run(
                "git clean -fd",
                shell=True, cwd=str(work_dir),
                capture_output=True, text=True, timeout=30,
            )
        except Exception:
            pass

    # --- P0-1 + P0-3: File change detection helpers ---

    @staticmethod
    def _git_changed_files(work_dir: Path) -> list[str]:
        """Get list of changed files relative to HEAD."""
        try:
            proc = subprocess.run(
                "git diff --name-only HEAD",
                shell=True, cwd=str(work_dir),
                capture_output=True, text=True, timeout=15,
            )
            if proc.returncode == 0:
                return [
                    f
                    for f in proc.stdout.strip().splitlines()
                    if f and not AutoCodeAdapter._is_benchmark_bookkeeping_path(f)
                ]
        except Exception:
            pass
        return []

    @staticmethod
    def _is_benchmark_bookkeeping_path(path: str) -> bool:
        """Return True for generated benchmark/runtime files, not source edits."""
        if path in BENCHMARK_BOOKKEEPING_FILES:
            return True
        if path.endswith((".pyc", ".pyo")):
            return True
        if path.startswith("__pycache__/") or "/__pycache__/" in path:
            return True
        if path.startswith(".pytest_cache/") or "/.pytest_cache/" in path:
            return True
        return False

    @staticmethod
    def _git_restore_files(
        work_dir: Path, file_paths: list[str],
    ) -> None:
        """Restore specific files to their HEAD state."""
        if not file_paths:
            return
        try:
            files_str = " ".join(f'"{f}"' for f in file_paths)
            subprocess.run(
                f"git checkout HEAD -- {files_str}",
                shell=True, cwd=str(work_dir),
                capture_output=True, text=True, timeout=15,
            )
        except Exception:
            pass

    @staticmethod
    def _git_diff_content(work_dir: Path) -> str:
        """Get full diff content for hashing."""
        try:
            proc = subprocess.run(
                "git diff HEAD",
                shell=True, cwd=str(work_dir),
                capture_output=True, text=True, timeout=15,
            )
            if proc.returncode == 0:
                return proc.stdout
        except Exception:
            pass
        return ""
