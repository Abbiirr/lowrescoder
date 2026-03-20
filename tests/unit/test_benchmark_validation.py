"""Tests for NOT_EXECUTABLE manifest validation (Phase 3)."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from benchmarks.adapters.base import BenchmarkTask  # noqa: E402
from benchmarks.benchmark_runner import validate_lane_executable  # noqa: E402


def _make_task(
    task_id: str = "t1",
    setup_commands: list[str] | None = None,
    grading_command: str = "",
    **extra: object,
) -> BenchmarkTask:
    return BenchmarkTask(
        task_id=task_id,
        description="test task",
        repo="",
        difficulty="easy",
        language="python",
        category="test",
        setup_commands=setup_commands or [],
        grading_command=grading_command,
        extra=dict(extra),
    )


class TestValidateLaneExecutable:
    """Tests for validate_lane_executable()."""

    def test_calculator_always_executable(self) -> None:
        ok, reason = validate_lane_executable(
            "B6", {"runner": "calculator"}, {}, [],
        )
        assert ok is True
        assert reason == ""

    def test_swebench_valid_manifest(self) -> None:
        tasks = [
            _make_task(
                setup_commands=["pip install -e ."],
                grading_command="pytest tests/",
                python_version="3.11",
            ),
        ]
        ok, reason = validate_lane_executable(
            "B7", {"runner": "swebench"}, {}, tasks,
        )
        assert ok is True

    def test_swebench_skeletal_not_executable(self) -> None:
        tasks = [_make_task()]  # No setup, no grading, no python_version
        ok, reason = validate_lane_executable(
            "B10", {"runner": "swebench"}, {}, tasks,
        )
        assert ok is False
        assert "skeletal" in reason.lower() or "setup_commands" in reason

    def test_swebench_missing_grading_not_executable(self) -> None:
        tasks = [
            _make_task(
                setup_commands=["pip install -e ."],
                python_version="3.11",
            ),
        ]
        ok, reason = validate_lane_executable(
            "B10", {"runner": "swebench"}, {}, tasks,
        )
        assert ok is False

    def test_swebench_with_docker_image(self) -> None:
        tasks = [
            _make_task(
                setup_commands=["apt install -y rustc"],
                grading_command="cargo test",
                docker_image="rust:1.75-slim",
            ),
        ]
        ok, reason = validate_lane_executable(
            "B10", {"runner": "swebench"}, {}, tasks,
        )
        assert ok is True

    def test_terminalbench_with_harbor_dataset(self) -> None:
        meta = {"harbor_dataset": "terminal-bench@2.0"}
        ok, reason = validate_lane_executable(
            "B9", {"runner": "terminalbench"}, meta, [],
        )
        assert ok is True

    def test_terminalbench_with_verifier_kind(self) -> None:
        meta = {"verifier_kind": "official"}
        ok, reason = validate_lane_executable(
            "B9", {"runner": "terminalbench"}, meta, [],
        )
        assert ok is True

    def test_terminalbench_no_meta_not_executable(self) -> None:
        ok, reason = validate_lane_executable(
            "B9", {"runner": "terminalbench"}, {}, [_make_task()],
        )
        assert ok is False
        assert "harbor_dataset" in reason or "verifier_kind" in reason

    def test_terminalbench_with_grading_command(self) -> None:
        tasks = [_make_task(grading_command="./verify.sh")]
        ok, reason = validate_lane_executable(
            "B9", {"runner": "terminalbench"}, {}, tasks,
        )
        assert ok is True

    def test_competitive_valid_manifest(self) -> None:
        tasks = [
            _make_task(
                grading_command="python grader.py",
                fixture_dir="fixtures/b13/cc-001-two-sum",
            ),
        ]
        ok, reason = validate_lane_executable(
            "B13-PROXY", {"runner": "competitive"}, {}, tasks,
        )
        assert ok is True

    def test_competitive_no_fixture_not_executable(self) -> None:
        tasks = [_make_task(grading_command="python grader.py")]
        ok, reason = validate_lane_executable(
            "B13-PROXY", {"runner": "competitive"}, {}, tasks,
        )
        assert ok is False
        assert "fixture_dir" in reason

    def test_competitive_no_grading_not_executable(self) -> None:
        tasks = [
            _make_task(fixture_dir="fixtures/b13/cc-001-two-sum"),
        ]
        ok, reason = validate_lane_executable(
            "B13-PROXY", {"runner": "competitive"}, {}, tasks,
        )
        assert ok is False

    def test_unknown_runner_assumed_executable(self) -> None:
        ok, reason = validate_lane_executable(
            "BXXX", {"runner": "unknown_future_runner"}, {}, [],
        )
        assert ok is True

    def test_empty_tasks_swebench_not_executable(self) -> None:
        ok, reason = validate_lane_executable(
            "B7", {"runner": "swebench"}, {}, [],
        )
        assert ok is False
