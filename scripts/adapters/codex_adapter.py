"""Codex CLI agent adapter — runs tasks through OpenAI Codex CLI.

Uses user's Codex subscription (no per-API cost).
Provider mode: subscription.
"""

from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path

from .base import AgentResult, BenchmarkTask, BudgetProfile


class CodexAdapter:
    """Runs benchmark tasks through the Codex CLI (user subscription)."""

    def __init__(self, model: str = ""):
        self._model = model or "gpt-4o"

    @property
    def name(self) -> str:
        return "codex"

    @property
    def version(self) -> str:
        exe = shutil.which("codex")
        if exe:
            try:
                proc = subprocess.run(
                    ["codex", "--version"],
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
        """Run Codex CLI on the task."""
        start = time.monotonic()
        error = ""
        output = ""
        resolved = False

        codex_exe = shutil.which("codex")
        if not codex_exe:
            return AgentResult(
                task_id=task.task_id,
                resolved=False,
                error="codex CLI not found on PATH",
            )

        prompt = f"Fix this issue: {task.description}"
        cmd = [
            codex_exe,
            "--model", self._model,
            "--approval-mode", "full-auto",
            "-q",  # quiet mode
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
            else:
                resolved = True
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
