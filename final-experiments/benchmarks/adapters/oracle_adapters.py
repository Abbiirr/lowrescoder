"""Synthetic oracle adapters — deterministic ground-truth probes for harness calibration.

These adapters never touch the network. They apply a *known* action to the sandbox so the
harness's grading path can be checked against a known-correct outcome:

* ``GoldenOracle`` applies the task's reference solution (``task.extra['gold_files']``) →
  grading MUST report PASS. Catches **false negatives** (harness failing a correct fix).
* ``NoopOracle`` makes no change → grading MUST report FAIL. Catches the degenerate
  "empty diff scored as pass" bug.
* ``WrongOracle`` applies a plausible-but-wrong change (``task.extra['wrong_files']``) →
  grading MUST report FAIL. Catches **false positives** — the SWE-bench-Verified failure
  mode where a logically-wrong patch slips past a weak test.

Together with the real ``PukuAdapter`` (which exercises the live agent path), the oracles
bound both error directions of the grader: golden/puku check that correct work passes,
noop/wrong check that incorrect work fails.

Each oracle applies its files, then runs the task's ``grading_command`` through the same
host/Docker path the real adapters use, and reports ``resolved`` from the grade. The
calibration suite asserts the expected verdict per oracle.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from benchmarks.docker_helpers import docker_exec as _docker_exec

from .base import AgentResult, BenchmarkTask, BudgetProfile


def _work_dir(task: BenchmarkTask, sandbox: Path) -> Path:
    if task.extra.get("fixture_dir"):
        return sandbox
    repo_name = task.extra.get("repo_name", "")
    if repo_name and (sandbox / repo_name).is_dir():
        return sandbox / repo_name
    return sandbox


def _write_files(work_dir: Path, files: dict[str, str]) -> list[str]:
    written: list[str] = []
    for rel, content in (files or {}).items():
        target = work_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        written.append(rel)
    return written


def _run_grading(task: BenchmarkTask, sandbox: Path) -> tuple[int, str]:
    container = task.extra.get("_container_name")
    if container:
        res = _docker_exec(container, task.grading_command, timeout=120)
        return res.returncode, (res.stdout + res.stderr)
    # Resolve `python`/`pytest` in grading commands against the running
    # interpreter's bin dir, so grading is deterministic whether the suite is
    # launched via `uv run` (venv on PATH) or a bare `.venv/bin/python`.
    env = os.environ.copy()
    env["PATH"] = os.pathsep.join([str(Path(sys.executable).parent), env.get("PATH", "")])
    res = subprocess.run(
        task.grading_command,
        shell=True, cwd=str(sandbox), env=env,
        capture_output=True, text=True, timeout=120,
    )
    return res.returncode, ((res.stdout or "") + (res.stderr or ""))


class _BaseOracle:
    """Shared oracle behaviour: apply files, grade, report."""

    _oracle_name = "oracle"
    _files_key: str | None = None          # task.extra key for files to write
    _expected_resolved = False             # what a correct grader SHOULD return

    def __init__(self, model: str = ""):
        self._model = model or "oracle"

    @property
    def name(self) -> str:
        return self._oracle_name

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def provider_mode(self) -> str:
        return "local_free"

    @property
    def model(self) -> str:
        return self._model

    def pre_task_healthcheck(self) -> None:
        return None

    async def solve_task(
        self,
        task: BenchmarkTask,
        sandbox: Path,
        budget: BudgetProfile,
    ) -> AgentResult:
        start = time.monotonic()
        work_dir = _work_dir(task, sandbox)
        written: list[str] = []
        if self._files_key:
            written = _write_files(work_dir, task.extra.get(self._files_key, {}))

        resolved = False
        grading_output = ""
        rc = -1
        error = ""
        if task.grading_command:
            try:
                rc, grading_output = _run_grading(task, sandbox)
                resolved = rc == 0
            except Exception as e:  # noqa: BLE001
                error = f"{type(e).__name__}: {e}"
        else:
            error = "oracle calibration requires a grading_command"

        return AgentResult(
            task_id=task.task_id,
            resolved=resolved,
            score=1.0 if resolved else 0.0,
            wall_time_s=round(time.monotonic() - start, 3),
            error=error,
            output=grading_output[:1000],
            artifacts={
                "agent": self._oracle_name,
                "oracle_expected_resolved": self._expected_resolved,
                "oracle_files_written": written,
                "grading_returncode": rc,
                "failure_type": "RESOLVED" if resolved else "WRONG_FIX",
            } | self._extra_artifacts(),  # type: ignore[operator]
        )

    def _extra_artifacts(self) -> dict[str, Any]:
        return {}


class GoldenOracle(_BaseOracle):
    """Applies the reference solution; grading must PASS."""

    _oracle_name = "oracle-golden"
    _files_key = "gold_files"
    _expected_resolved = True


class NoopOracle(_BaseOracle):
    """Applies nothing; grading must FAIL."""

    _oracle_name = "oracle-noop"
    _files_key = None
    _expected_resolved = False


class WrongOracle(_BaseOracle):
    """Applies a plausible-but-wrong change; grading must FAIL."""

    _oracle_name = "oracle-wrong"
    _files_key = "wrong_files"
    _expected_resolved = False


ORACLE_ADAPTERS: dict[str, type[_BaseOracle]] = {
    "oracle-golden": GoldenOracle,
    "oracle-noop": NoopOracle,
    "oracle-wrong": WrongOracle,
}
