"""Claude Code CLI agent adapter — runs tasks through Claude Code CLI.

Uses user's Claude Code subscription (no per-API cost).
Provider mode: subscription.
"""

from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path

from scripts.docker_helpers import docker_exec as _docker_exec

from .base import AgentResult, BenchmarkTask, BudgetProfile


class ClaudeCodeAdapter:
    """Runs benchmark tasks through the Claude Code CLI (user subscription)."""

    def __init__(self, model: str = ""):
        self._model = model or "claude-sonnet-4-5-20250929"

    @property
    def name(self) -> str:
        return "claude-code"

    @property
    def version(self) -> str:
        exe = shutil.which("claude")
        if exe:
            try:
                proc = subprocess.run(
                    ["claude", "--version"],
                    capture_output=True, text=True, timeout=10,
                )
                return proc.stdout.strip() or "unknown"
            except Exception:
                pass
        return "unknown"

    @property
    def provider_mode(self) -> str:
        return "subscription"

    @property
    def model(self) -> str:
        return self._model

    async def solve_task(
        self,
        task: BenchmarkTask,
        sandbox: Path,
        budget: BudgetProfile,
    ) -> AgentResult:
        """Run Claude Code CLI on the task."""
        start = time.monotonic()
        error = ""
        output = ""
        resolved = False

        claude_exe = shutil.which("claude")
        if not claude_exe:
            return AgentResult(
                task_id=task.task_id,
                resolved=False,
                error="claude CLI not found on PATH",
            )

        prompt = f"Fix this issue: {task.description}"
        cmd = [
            claude_exe,
            "--model", self._model,
            "-p",  # print mode (non-interactive)
            prompt,
        ]

        try:
            proc = subprocess.run(
                cmd,
                cwd=str(sandbox),
                capture_output=True,
                text=True,
                timeout=budget.wall_time_s,
            )
            output = proc.stdout[:2000]
            if proc.returncode != 0:
                error = proc.stderr[:1000]

            # Grading: use grading_command if available, else CLI exit code
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
                    )
                resolved = grade_result.returncode == 0
                if not resolved:
                    output += (
                        f"\n--- Grading ---\n"
                        f"Exit code: {grade_result.returncode}\n"
                        f"stdout: {grade_result.stdout[:500]}\n"
                        f"stderr: {grade_result.stderr[:500]}"
                    )
            else:
                resolved = proc.returncode == 0
        except subprocess.TimeoutExpired:
            error = f"Timeout after {budget.wall_time_s}s"
        except Exception as e:
            error = str(e)

        elapsed = time.monotonic() - start

        return AgentResult(
            task_id=task.task_id,
            resolved=resolved,
            wall_time_s=round(elapsed, 1),
            error=error,
            output=output,
        )
