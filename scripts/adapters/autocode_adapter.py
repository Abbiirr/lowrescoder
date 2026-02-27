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

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from scripts.docker_helpers import docker_exec as _docker_exec  # noqa: E402

from .base import AgentResult, BenchmarkTask, BudgetProfile  # noqa: E402

# --- Retry loop constants ---
MAX_GRADE_ATTEMPTS = 3
MIN_ATTEMPT_BUDGET_S = 60

# --- Provider classification ---

def classify_provider_mode(provider: str, model: str) -> str:
    """Classify a provider+model pair into a cost mode.

    Returns 'local_free', or 'paid_metered'.  Fails closed to paid_metered
    for unknown providers so the runner can block them by policy.
    """
    if provider == "ollama":
        return "local_free"
    if provider == "openrouter":
        return "local_free" if model.endswith(":free") else "paid_metered"
    return "paid_metered"  # fail closed


# --- Tool restriction ---
BASH_ONLY_TOOLS: frozenset[str] = frozenset({"run_command", "read_file"})


class AutoCodeAdapter:
    """Runs benchmark tasks through AutoCode's AgentLoop with Ollama."""

    def __init__(self, model: str = ""):
        self._provider = os.environ.get(
            "AUTOCODE_LLM_PROVIDER", "ollama",
        )
        if self._provider == "openrouter":
            self._model = model or os.environ.get("OPENROUTER_MODEL", "")
        else:
            self._model = model or os.environ.get("OLLAMA_MODEL", "")
        if not self._model:
            raise ValueError(
                "No model specified. Set --model, OLLAMA_MODEL, or OPENROUTER_MODEL."
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

    def _find_work_dir(self, sandbox: Path, task: BenchmarkTask) -> Path:
        """Find the actual working directory for the agent.

        For SWE-bench tasks, the repo is cloned into sandbox/repo_name.
        For other tasks, use the sandbox directly.
        """
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
            from autocode.agent.loop import AgentLoop
            from autocode.agent.tools import create_default_registry
            from autocode.config import ShellConfig, load_config
            from autocode.layer4.llm import create_provider
            from autocode.session.store import SessionStore

            # Determine working directory
            work_dir = self._find_work_dir(sandbox, task)

            # Load config, override for benchmark
            config = load_config(project_root=PROJECT_ROOT)
            config.llm.model = self._model
            config.llm.provider = self._provider
            if self._provider == "openrouter":
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

                # Register run_tests tool for Docker mode
                _container_name = task.extra.get("_container_name")
                if _container_name and task.grading_command:
                    from autocode.agent.tools import ToolDefinition

                    _cname_for_closure = _container_name
                    _gcmd_for_closure = task.grading_command

                    def _handle_run_tests(**_kwargs: Any) -> str:
                        """Run the grading tests in the Docker container."""
                        try:
                            result = _docker_exec(
                                _cname_for_closure,
                                _gcmd_for_closure,
                                timeout=120,
                            )
                            output = (
                                result.stdout + result.stderr
                            )
                            # Truncate to last 2000 chars
                            if len(output) > 2000:
                                output = "...(truncated)\n" + output[-2000:]
                            if result.returncode == 0:
                                return f"PASSED\n{output}"
                            return f"FAILED (exit code {result.returncode})\n{output}"
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

                # Enforce tool restriction (B8 bash-only lane)
                tool_restriction = task.extra.get("tool_restriction")
                enforced_policy = None
                if tool_restriction == "bash-only":
                    allowed = set(BASH_ONLY_TOOLS)
                    # Include run_tests if registered (Docker mode)
                    if _container_name and task.grading_command:
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

                loop = AgentLoop(
                    provider=provider,
                    tool_registry=registry,
                    approval_manager=approval_mgr,
                    session_store=session_store,
                    session_id=session_id,
                )

                # Track tool calls
                def on_tool_call(
                    name: str, status: str, result: str,
                ) -> None:
                    nonlocal tool_call_count
                    if status == "running":
                        tool_call_count += 1

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
                _cname_init = task.extra.get("_container_name")
                if _cname_init and task.grading_command:
                    try:
                        init_result = _docker_exec(
                            _cname_init,
                            task.grading_command,
                            timeout=120,
                        )
                        raw_output = init_result.stdout + init_result.stderr
                        # Take last 1500 chars to keep prompt reasonable
                        if len(raw_output) > 1500:
                            initial_test_output = (
                                "...(truncated)\n" + raw_output[-1500:]
                            )
                        else:
                            initial_test_output = raw_output
                    except Exception:
                        pass  # Non-critical: agent can still run_tests

                # Build initial prompt
                prompt = self._build_prompt(
                    task,
                    initial_test_output=initial_test_output,
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

                # --- Outer grading retry loop ---
                for attempt in range(MAX_GRADE_ATTEMPTS):
                    elapsed_so_far = time.monotonic() - start
                    remaining = budget.wall_time_s - elapsed_so_far
                    if remaining < MIN_ATTEMPT_BUDGET_S:
                        break

                    # P0-6: Restore baseline before retries
                    if attempt > 0:
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
                    test_files_changed = bool(
                        test_patch_files
                        and set(changed_files) & set(test_patch_files)
                    )

                    # P0-1: Restore test files if agent edited them
                    if test_files_changed:
                        self._git_restore_files(
                            work_dir, test_patch_files,
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
                        if _cname:
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
                            "diff_hash": diff_hash,
                            "grading_output_path": str(grading_path),
                        })

                        if resolved:
                            break

                        # P0-4: Stagnation detection
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

                        # P0-2: Structured failure feedback
                        prompt = self._build_feedback_prompt(
                            grading_output,
                            task.grading_command,
                            changed_files=changed_files,
                            test_files_changed=test_files_changed,
                            stagnation_count=stagnation_count,
                            docker_grading=bool(
                                task.extra.get("_container_name"),
                            ),
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

        artifacts: dict = {"grade_attempts": grade_attempts}
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
    ) -> str:
        """Build the agent prompt from the task."""
        fail_tests = task.extra.get("FAIL_TO_PASS", [])
        test_list = (
            "\n".join(f"  - {t}" for t in fail_tests) if fail_tests else ""
        )
        # Docker tasks: agent should NOT run grading command on host
        # because grading runs in the container via the harness retry loop.
        docker_grading = bool(task.extra.get("_container_name"))

        prompt = (
            f"You are a coding agent working in a "
            f"{task.repo or 'Python'} repository.\n\n"
            "IMPORTANT: The test patch has already been pre-applied. "
            "The failing tests are already in the codebase. "
            "You MUST fix the SOURCE CODE only — do NOT modify any test "
            "files.\n\n"
            f"BUG REPORT:\n{task.description}\n\n"
        )

        if test_list:
            prompt += (
                f"FAILING TESTS (must pass after your fix):\n"
                f"{test_list}\n\n"
            )

        if task.grading_command and not docker_grading:
            prompt += (
                f"GRADING COMMAND (use this to check your fix):\n"
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
                    "Step 4: Use run_command with sed, tee, or similar "
                    "shell commands to edit the SOURCE code. Make the "
                    "MINIMUM change needed.\n"
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
                    "- Use run_command with sed/tee/echo to edit files.\n"
                )
            else:
                prompt += (
                    "- Use edit_file (NOT write_file) for editing "
                    "existing files.\n"
                )
            prompt += (
                "- If you receive feedback that tests failed, read the "
                "error output and adjust your fix."
            )
        elif bash_only:
            prompt += (
                "MANDATORY WORKFLOW — follow these steps exactly:\n"
                "Step 1: Run the grading command above to see the current "
                "test failures and read the output carefully.\n"
                "Step 2: Use read_file to read the SOURCE file(s) that "
                "need fixing (NOT the test files).\n"
                "Step 3: Understand what the tests expect and what the "
                "source code does wrong.\n"
                "Step 4: Use run_command with sed, tee, or similar shell "
                "commands to edit the SOURCE code. Make the MINIMUM "
                "change needed.\n"
                "Step 5: Run the grading command again to verify tests "
                "pass.\n"
                "Step 6: If tests still fail, read the error output, "
                "adjust your fix, and repeat from Step 4.\n\n"
                "RULES:\n"
                "- You MUST call tools. Do NOT just describe the fix.\n"
                "- Do NOT modify test files — they are already correct.\n"
                "- Fix the SOURCE code that the tests exercise.\n"
                "- You only have run_command and read_file available.\n"
                "- Use run_command with sed/tee/echo to edit files.\n"
                "- After writing your fix, ALWAYS run the grading "
                "command to verify.\n"
                "- If tests fail, read the error output and iterate."
            )
        else:
            prompt += (
                "MANDATORY WORKFLOW — follow these steps exactly:\n"
                "Step 1: Run the grading command above to see the current "
                "test failures and read the output carefully.\n"
                "Step 2: Use read_file to read the SOURCE file(s) that "
                "need fixing (NOT the test files).\n"
                "Step 3: Understand what the tests expect and what the "
                "source code does wrong.\n"
                "Step 4: Use edit_file to fix the SOURCE code. Make the "
                "MINIMUM change needed. Use edit_file (NOT write_file) "
                "for editing existing files.\n"
                "Step 5: Run the grading command again to verify tests "
                "pass.\n"
                "Step 6: If tests still fail, read the error output, "
                "adjust your fix, and repeat from Step 4.\n\n"
                "RULES:\n"
                "- You MUST call tools. Do NOT just describe the fix.\n"
                "- Do NOT modify test files — they are already correct.\n"
                "- Fix the SOURCE code that the tests exercise.\n"
                "- Use edit_file (NOT write_file) for editing existing "
                "files.\n"
                "- After writing your fix, ALWAYS run the grading "
                "command to verify.\n"
                "- If tests fail, read the error output and iterate."
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

    def _build_feedback_prompt(
        self,
        grading_output: str,
        grading_command: str,
        *,
        changed_files: list[str] | None = None,
        test_files_changed: bool = False,
        stagnation_count: int = 0,
        docker_grading: bool = False,
    ) -> str:
        """Build a structured feedback prompt after a failed attempt."""
        parts: list[str] = []

        # Policy violation warning
        if test_files_changed:
            parts.append(
                "WARNING: Your previous attempt edited test files. "
                "Those edits have been REVERTED. You MUST fix SOURCE "
                "code only — do NOT modify any test files."
            )

        # Stagnation warning
        if stagnation_count >= 1:
            parts.append(
                "WARNING: You are repeating the same fix. Try a "
                "DIFFERENT approach: read the failing test more "
                "carefully, look at related source files, or "
                "consider a different fix strategy."
            )

        # Previous attempt context
        if changed_files:
            parts.append(
                "Files you changed in previous attempt:\n"
                + "\n".join(f"  - {f}" for f in changed_files)
            )

        # Structured failure info
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

        # Tail of raw output (reduced to leave room for structure)
        max_tail = 1500
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

    # --- P0-6: Git checkpoint helpers ---

    @staticmethod
    def _git_create_baseline(work_dir: Path) -> bool:
        """Create a git baseline commit after test patch apply.

        Returns True if baseline was created successfully.
        Raises RuntimeError if commit fails — all downstream
        enforcement depends on a valid baseline.
        """
        try:
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
                    f for f in proc.stdout.strip().splitlines() if f
                ]
        except Exception:
            pass
        return []

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
