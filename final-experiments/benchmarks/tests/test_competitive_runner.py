"""Tests for competitive runner (Phase 4)."""

from __future__ import annotations

import asyncio
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from benchmarks.adapters.base import (  # noqa: E402
    AgentResult,
    BenchmarkTask,
    BudgetProfile,
)
from benchmarks.benchmark_runner import (  # noqa: E402
    MANIFEST_DIR,
    _run_competitive_task,
    validate_lane_executable,
)


class TestFixtureCopyIntegration:
    """Test that fixture directories are structured correctly."""

    @pytest.mark.parametrize(
        "lane_dir,task_id",
        [
            ("b13", "cc-001-two-sum"),
            ("b13", "cc-009-valid-parentheses"),
            ("b14", "lcb-001-reverse-integer"),
            ("b14", "lcb-013-max-subarray"),
        ],
    )
    def test_fixture_structure(
        self, lane_dir: str, task_id: str,
    ) -> None:
        """Verify fixture directories have required files."""
        fixture_dir = MANIFEST_DIR / "fixtures" / lane_dir / task_id
        if not fixture_dir.exists():
            pytest.skip(f"Fixture dir not found: {fixture_dir}")

        assert (fixture_dir / "solution.py").exists(), "Missing solution.py"
        assert (fixture_dir / "grader.py").exists(), "Missing grader.py"
        assert (fixture_dir / "prompt.md").exists(), "Missing prompt.md"
        assert (
            fixture_dir / "tests" / "test_hidden.py"
        ).exists(), "Missing tests/test_hidden.py"

    @pytest.mark.parametrize(
        "lane_dir,task_id",
        [
            ("b13", "cc-001-two-sum"),
            ("b14", "lcb-005-climbing-stairs"),
        ],
    )
    def test_fixture_copy_to_sandbox(
        self, lane_dir: str, task_id: str,
    ) -> None:
        """Verify fixture files can be copied to a temp sandbox."""
        fixture_dir = MANIFEST_DIR / "fixtures" / lane_dir / task_id
        if not fixture_dir.exists():
            pytest.skip(f"Fixture dir not found: {fixture_dir}")

        with tempfile.TemporaryDirectory() as tmpdir:
            sandbox = Path(tmpdir)
            for item in fixture_dir.iterdir():
                dest = sandbox / item.name
                if item.is_dir():
                    shutil.copytree(item, dest)
                else:
                    shutil.copy2(item, dest)

            assert (sandbox / "solution.py").exists()
            assert (sandbox / "grader.py").exists()
            assert (sandbox / "tests" / "test_hidden.py").exists()


class TestCompetitiveValidation:
    """Test competitive runner validation."""

    def test_competitive_manifest_validates(self) -> None:
        """B13 manifest should pass validation with fixture_dir."""
        tasks = [
            BenchmarkTask(
                task_id="cc-001-two-sum",
                description="test",
                repo="",
                difficulty="easy",
                language="python",
                category="arrays",
                setup_commands=[],
                grading_command="python grader.py",
                extra={"fixture_dir": "fixtures/b13/cc-001-two-sum"},
            ),
        ]
        ok, reason = validate_lane_executable(
            "B13-PROXY", {"runner": "competitive"}, {}, tasks,
        )
        assert ok is True

    def test_b13_manifest_all_tasks_have_fixtures(self) -> None:
        """Every B13 task should have fixture_dir in manifest."""
        import json
        manifest = MANIFEST_DIR / "b13-proxy-subset.json"
        if not manifest.exists():
            pytest.skip("B13 manifest not found")
        data = json.loads(manifest.read_text())
        for task in data["tasks"]:
            assert "fixture_dir" in task, (
                f"Task {task['task_id']} missing fixture_dir"
            )
            assert "grading_command" in task, (
                f"Task {task['task_id']} missing grading_command"
            )

    def test_b14_manifest_all_tasks_have_fixtures(self) -> None:
        """Every B14 task should have fixture_dir in manifest."""
        import json
        manifest = MANIFEST_DIR / "b14-proxy-subset.json"
        if not manifest.exists():
            pytest.skip("B14 manifest not found")
        data = json.loads(manifest.read_text())
        for task in data["tasks"]:
            assert "fixture_dir" in task, (
                f"Task {task['task_id']} missing fixture_dir"
            )
            assert "grading_command" in task, (
                f"Task {task['task_id']} missing grading_command"
            )


class _FakeAgent:
    """Minimal mock agent for testing _run_competitive_task()."""

    name = "fake"
    version = "0.0.0"
    provider_mode = "local_free"
    model = "fake-model"

    def __init__(self, write_solution: str | None = None) -> None:
        self._write_solution = write_solution
        self.received_task: BenchmarkTask | None = None

    async def solve_task(
        self,
        task: BenchmarkTask,
        sandbox: Path,
        budget: BudgetProfile,
    ) -> AgentResult:
        self.received_task = task
        if self._write_solution:
            (sandbox / "solution.py").write_text(self._write_solution)
        return AgentResult(
            task_id=task.task_id,
            resolved=False,
            wall_time_s=1.0,
            tool_calls=1,
        )


class TestRunCompetitiveTask:
    """Tests for _run_competitive_task() end-to-end."""

    def _make_fixture(self, tmpdir: Path) -> Path:
        """Create a minimal fixture directory."""
        fixture = tmpdir / "fixture"
        fixture.mkdir()
        (fixture / "prompt.md").write_text("Solve two-sum problem.")
        (fixture / "solution.py").write_text(
            "def two_sum(nums, target):\n    pass\n",
        )
        tests_dir = fixture / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_hidden.py").write_text(
            "from solution import two_sum\n"
            "def test_basic():\n"
            "    assert two_sum([2, 7, 11, 15], 9) == [0, 1]\n",
        )
        (fixture / "grader.py").write_text(
            "import subprocess, sys\n"
            "r = subprocess.run(\n"
            "    [sys.executable, '-m', 'pytest', 'tests/', '-q'],\n"
            "    capture_output=True, text=True,\n"
            ")\n"
            "sys.exit(r.returncode)\n",
        )
        return fixture

    def test_missing_fixture_dir_returns_error(self) -> None:
        """Task with no fixture_dir should return error."""
        task = BenchmarkTask(
            task_id="t1", description="test", repo="",
            difficulty="easy", language="python", category="test",
            setup_commands=[], grading_command="python grader.py",
            extra={},
        )
        agent = _FakeAgent()
        budget = BudgetProfile()
        with tempfile.TemporaryDirectory() as tmpdir:
            result = asyncio.run(
                _run_competitive_task(agent, task, Path(tmpdir), budget),
            )
        assert result.resolved is False
        assert "fixture_dir" in result.error

    def test_nonexistent_fixture_dir_returns_error(self) -> None:
        """Task with fixture_dir pointing to nonexistent path."""
        task = BenchmarkTask(
            task_id="t1", description="test", repo="",
            difficulty="easy", language="python", category="test",
            setup_commands=[], grading_command="python grader.py",
            extra={"fixture_dir": "fixtures/nonexistent/task"},
        )
        agent = _FakeAgent()
        budget = BudgetProfile()
        with tempfile.TemporaryDirectory() as tmpdir:
            result = asyncio.run(
                _run_competitive_task(agent, task, Path(tmpdir), budget),
            )
        assert result.resolved is False
        assert "not found" in result.error

    def test_fixture_copied_and_agent_receives_prompt(self) -> None:
        """Fixture files are copied and agent gets problem description."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            fixture = self._make_fixture(tmppath)
            sandbox = tmppath / "sandbox"
            sandbox.mkdir()

            task = BenchmarkTask(
                task_id="cc-test", description="test", repo="",
                difficulty="easy", language="python", category="test",
                setup_commands=[],
                grading_command="python grader.py",
                extra={"fixture_dir": str(fixture)},
            )
            agent = _FakeAgent()
            budget = BudgetProfile()
            # Uses absolute fixture_dir path to bypass MANIFEST_DIR
            asyncio.run(
                _run_competitive_task(agent, task, sandbox, budget),
            )
            # Agent should have received the task
            assert agent.received_task is not None
            assert "two-sum" in agent.received_task.description.lower() or \
                "Solve" in agent.received_task.description
            # Fixture files should be in sandbox
            assert (sandbox / "solution.py").exists()
            assert (sandbox / "grader.py").exists()
            assert (sandbox / "tests" / "test_hidden.py").exists()

    def test_grading_passes_with_correct_solution(self) -> None:
        """If agent writes correct solution, grading should pass."""
        correct_solution = (
            "def two_sum(nums, target):\n"
            "    lookup = {}\n"
            "    for i, n in enumerate(nums):\n"
            "        if target - n in lookup:\n"
            "            return [lookup[target - n], i]\n"
            "        lookup[n] = i\n"
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            fixture = self._make_fixture(tmppath)
            sandbox = tmppath / "sandbox"
            sandbox.mkdir()

            task = BenchmarkTask(
                task_id="cc-test", description="test", repo="",
                difficulty="easy", language="python", category="test",
                setup_commands=[],
                grading_command="python grader.py",
                extra={"fixture_dir": str(fixture)},
            )
            agent = _FakeAgent(write_solution=correct_solution)
            budget = BudgetProfile()
            result = asyncio.run(
                _run_competitive_task(agent, task, sandbox, budget),
            )
            assert result.resolved is True
            assert result.score == 1.0

    def test_grading_fails_with_stub_solution(self) -> None:
        """Stub solution should fail grading."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            fixture = self._make_fixture(tmppath)
            sandbox = tmppath / "sandbox"
            sandbox.mkdir()

            task = BenchmarkTask(
                task_id="cc-test", description="test", repo="",
                difficulty="easy", language="python", category="test",
                setup_commands=[],
                grading_command="python grader.py",
                extra={"fixture_dir": str(fixture)},
            )
            # Agent does NOT write a solution — stub remains
            agent = _FakeAgent()
            budget = BudgetProfile()
            result = asyncio.run(
                _run_competitive_task(agent, task, sandbox, budget),
            )
            assert result.resolved is False
