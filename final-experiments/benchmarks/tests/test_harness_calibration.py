"""Harness calibration — deterministic oracle invariants.

These tests validate the *harness*, not any agent. They run synthetic oracle adapters
(golden / noop / wrong) against self-contained calibration tasks with known outcomes and
assert that the grading path classifies them correctly. They are network-free and must
hard-assert (no skips): a failure here means the grader itself is untrustworthy.

The live agent (puku-cli) calibration lives in ``benchmarks/calibrate_harness.py`` so this
file never depends on the gateway being up.

Invariants covered:
* No false negatives  — GoldenOracle ⇒ PASS on every task.
* No false positives   — NoopOracle and WrongOracle ⇒ FAIL on every task.
* Determinism          — repeated runs of the same oracle/task give the same verdict.
* Isolation            — separate task sandboxes never share files.
"""

from __future__ import annotations

import asyncio

import pytest

from benchmarks.adapters.base import BudgetProfile
from benchmarks.adapters.oracle_adapters import (
    GoldenOracle,
    NoopOracle,
    WrongOracle,
)
from benchmarks.calibration_tasks import CALIBRATION_TASKS, CalibrationTask

_BUDGET = BudgetProfile(wall_time_s=120, token_cap=1000, max_tool_calls=1)


def _run(task: CalibrationTask, oracle) -> bool:
    sandbox = task.make_sandbox()
    try:
        result = asyncio.run(oracle.solve_task(task.to_benchmark_task(), sandbox, _BUDGET))
        return result.resolved
    finally:
        import shutil

        shutil.rmtree(sandbox, ignore_errors=True)


@pytest.mark.parametrize("task", CALIBRATION_TASKS, ids=lambda t: t.task_id)
def test_golden_oracle_passes(task: CalibrationTask) -> None:
    """A correct solution must be graded PASS (no false negatives)."""
    assert _run(task, GoldenOracle()) is True, (
        f"GoldenOracle failed grading on {task.task_id} — the harness is rejecting a "
        f"known-correct solution (false negative)."
    )


@pytest.mark.parametrize("task", CALIBRATION_TASKS, ids=lambda t: t.task_id)
def test_noop_oracle_fails(task: CalibrationTask) -> None:
    """An empty (no-edit) sandbox must be graded FAIL."""
    assert _run(task, NoopOracle()) is False, (
        f"NoopOracle passed grading on {task.task_id} — the harness scores a no-op as a "
        f"pass (false positive on empty diff)."
    )


@pytest.mark.parametrize("task", CALIBRATION_TASKS, ids=lambda t: t.task_id)
def test_wrong_oracle_fails(task: CalibrationTask) -> None:
    """A plausible-but-wrong solution must be graded FAIL (no false positives)."""
    assert _run(task, WrongOracle()) is False, (
        f"WrongOracle passed grading on {task.task_id} — the harness accepts a logically "
        f"wrong solution (false positive; the SWE-bench-Verified failure mode)."
    )


@pytest.mark.parametrize("task", CALIBRATION_TASKS, ids=lambda t: t.task_id)
def test_grading_is_deterministic(task: CalibrationTask) -> None:
    """Repeated runs of the same oracle/task yield the same verdict."""
    reps = 5
    golden = [_run(task, GoldenOracle()) for _ in range(reps)]
    noop = [_run(task, NoopOracle()) for _ in range(reps)]
    assert golden == [True] * reps, f"GoldenOracle verdict flipped on {task.task_id}: {golden}"
    assert noop == [False] * reps, f"NoopOracle verdict flipped on {task.task_id}: {noop}"


def test_sandbox_isolation() -> None:
    """Two task sandboxes are independent — no file leakage between them."""
    a = CALIBRATION_TASKS[1]  # calib-bugfix-add (writes calc.py)
    b = CALIBRATION_TASKS[2]  # calib-bugfix-clamp (writes util.py)
    sb_a = a.make_sandbox()
    sb_b = b.make_sandbox()
    try:
        # Solve A with golden; B must not see A's files and vice versa.
        asyncio.run(GoldenOracle().solve_task(a.to_benchmark_task(), sb_a, _BUDGET))
        assert (sb_a / "calc.py").exists()
        assert not (sb_b / "calc.py").exists(), "task B sandbox leaked task A's calc.py"
        assert not (sb_a / "util.py").exists(), "task A sandbox leaked task B's util.py"
    finally:
        import shutil

        shutil.rmtree(sb_a, ignore_errors=True)
        shutil.rmtree(sb_b, ignore_errors=True)
