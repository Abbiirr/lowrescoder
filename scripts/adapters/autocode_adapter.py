"""AutoCode agent adapter — runs tasks through AutoCode's AgentLoop.

Uses Ollama (local, free) by default. No API cost.
Provider mode: local_free.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import time
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from .base import AgentResult, BenchmarkTask, BudgetProfile  # noqa: E402


class AutoCodeAdapter:
    """Runs benchmark tasks through AutoCode's AgentLoop with Ollama."""

    def __init__(self, model: str = ""):
        self._provider = os.environ.get(
            "AUTOCODE_LLM_PROVIDER", "ollama",
        )
        if self._provider == "openrouter":
            self._model = model or os.environ.get(
                "OPENROUTER_MODEL", "z-ai/glm-4.5-air:free",
            )
        else:
            self._model = model or os.environ.get(
                "OLLAMA_MODEL", "qwen2.5-coder:14b-instruct-q4_K_M",
            )

    @property
    def name(self) -> str:
        return "autocode"

    @property
    def version(self) -> str:
        return "0.1.0"

    @property
    def provider_mode(self) -> str:
        return "local_free"

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
        """Run AutoCode AgentLoop on the task."""
        start = time.monotonic()
        tool_call_count = 0
        error = ""
        output = ""
        resolved = False

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

                # Build prompt with context
                prompt = self._build_prompt(task)

                # AgentLoop.run() returns a str
                result_text = await asyncio.wait_for(
                    loop.run(
                        prompt,
                        on_tool_call=on_tool_call,
                        approval_callback=approval_callback,
                        ask_user_callback=ask_user_callback,
                    ),
                    timeout=budget.wall_time_s,
                )
                output = result_text or ""

                # Grading: run grading command if provided
                if task.grading_command:
                    grade_result = subprocess.run(
                        task.grading_command,
                        shell=True,
                        cwd=str(sandbox),
                        capture_output=True,
                        text=True,
                        timeout=120,
                    )
                    resolved = grade_result.returncode == 0
                    if not resolved:
                        output += (
                            f"\n\n--- Grading ---\n"
                            f"Exit code: {grade_result.returncode}\n"
                            f"stdout: {grade_result.stdout[:500]}\n"
                            f"stderr: {grade_result.stderr[:500]}"
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

        return AgentResult(
            task_id=task.task_id,
            resolved=resolved,
            wall_time_s=round(elapsed, 1),
            tool_calls=tool_call_count,
            error=error,
            output=output[:2000],
        )

    def _build_prompt(self, task: BenchmarkTask) -> str:
        """Build the agent prompt from the task."""
        fail_tests = task.extra.get("FAIL_TO_PASS", [])
        test_list = "\n".join(f"  - {t}" for t in fail_tests) if fail_tests else ""

        prompt = (
            f"You are a coding agent working in a {task.repo or 'Python'} repository. "
            "You MUST use tools to fix bugs. NEVER just explain what to do — "
            "actually do it by calling tools.\n\n"
            f"BUG REPORT:\n{task.description}\n\n"
        )

        if test_list:
            prompt += (
                f"FAILING TESTS (must pass after your fix):\n{test_list}\n\n"
            )

        prompt += (
            "MANDATORY STEPS — follow these exactly using tools:\n"
            "Step 1: Use list_files to see the project structure.\n"
            "Step 2: Use read_file to read the source file(s) "
            "mentioned in the bug report.\n"
            "Step 3: Use read_file to read the failing test(s) "
            "to understand what the expected behavior is.\n"
            "Step 4: Use write_file to edit the source code and fix the bug. "
            "Make the MINIMUM change needed.\n"
            "Step 5: Use run_command to run the failing test(s) and "
            "confirm they pass.\n\n"
            "RULES:\n"
            "- You MUST call tools. Do NOT just describe the fix.\n"
            "- Do NOT modify test files.\n"
            "- Do NOT explain your reasoning without also taking action.\n"
            "- If you are unsure, read more files first, then fix.\n"
            "- After writing your fix, ALWAYS run the tests to verify."
        )

        return prompt
