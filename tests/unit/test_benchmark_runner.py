"""Tests for benchmark runner behavior (setup/patch failures, artifact serialization)."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.adapters.base import AgentResult, BenchmarkTask, BudgetProfile  # noqa: E402

from scripts.benchmark_runner import LANE_CONFIGS, run_lane  # noqa: E402  # isort: skip


def _make_agent(resolved: bool = True) -> MagicMock:
    """Create a mock agent adapter."""
    agent = MagicMock()
    agent.name = "test-agent"
    agent.version = "1.0"
    agent.model = "test-model"
    agent.provider_mode = "local_free"
    agent.solve_task = AsyncMock(return_value=AgentResult(
        task_id="test-task",
        resolved=resolved,
        wall_time_s=1.0,
        artifacts={"grade_attempts": [{"attempt": 1, "resolved": resolved}]},
    ))
    return agent


def _make_task(
    setup_commands: list[str] | None = None,
    test_patch: str = "",
    repo_name: str = "",
) -> BenchmarkTask:
    return BenchmarkTask(
        task_id="test-task",
        description="Test task",
        setup_commands=setup_commands or [],
        extra={"test_patch": test_patch, "repo_name": repo_name},
    )


# --- Setup failure handling ---


def test_setup_nonzero_rc_is_infra_fail():
    """Non-zero setup command rc should classify task as infra-fail."""
    agent = _make_agent()
    task = _make_task(setup_commands=["false"])  # 'false' returns rc=1
    budget = BudgetProfile(wall_time_s=60, token_cap=1000, max_tool_calls=10)

    # Mock subprocess.run to return non-zero for setup
    setup_result = MagicMock(returncode=1, stderr="setup error", stdout="")

    with patch("scripts.benchmark_runner.create_task_sandbox") as mock_sandbox, \
         patch("subprocess.run", return_value=setup_result):
        mock_sandbox.return_value = Path("/tmp/fake-sandbox")
        run_data = asyncio.run(
            run_lane(agent, "B7", [task], budget, None),
        )

    # Agent should NOT have been called (setup failed)
    agent.solve_task.assert_not_called()
    # Task should be marked as error/infra-fail
    assert run_data["results"][0]["error"] == "Setup failed"
    assert run_data["aggregate"]["infra_fails"] == 1


def test_setup_exception_is_infra_fail():
    """Setup command exception should classify task as infra-fail."""
    agent = _make_agent()
    task = _make_task(setup_commands=["will-fail"])
    budget = BudgetProfile(wall_time_s=60, token_cap=1000, max_tool_calls=10)

    with patch("scripts.benchmark_runner.create_task_sandbox") as mock_sandbox, \
         patch("subprocess.run", side_effect=OSError("cmd not found")):
        mock_sandbox.return_value = Path("/tmp/fake-sandbox")
        run_data = asyncio.run(
            run_lane(agent, "B7", [task], budget, None),
        )

    agent.solve_task.assert_not_called()
    assert run_data["results"][0]["error"] == "Setup failed"
    assert run_data["aggregate"]["infra_fails"] == 1


# --- Test patch failure handling ---


def test_patch_apply_failure_is_infra_fail(tmp_path: Path):
    """Failed git apply should classify task as infra-fail."""
    agent = _make_agent()
    task = _make_task(
        test_patch="invalid patch content",
        repo_name="myrepo",
    )
    budget = BudgetProfile(wall_time_s=60, token_cap=1000, max_tool_calls=10)

    # Create the repo dir so patch path exists
    repo_dir = tmp_path / "myrepo"
    repo_dir.mkdir()

    # Setup succeeds (no setup commands), but patch fails
    patch_result = MagicMock(returncode=1, stderr="patch error", stdout="")

    with patch("scripts.benchmark_runner.create_task_sandbox") as mock_sandbox, \
         patch("subprocess.run", return_value=patch_result):
        mock_sandbox.return_value = tmp_path
        run_data = asyncio.run(
            run_lane(agent, "B7", [task], budget, None),
        )

    agent.solve_task.assert_not_called()
    assert run_data["results"][0]["error"] == "Setup failed"


# --- Artifact serialization ---


def test_artifacts_persisted_in_results():
    """result.artifacts should be included in per-task output."""
    agent = _make_agent(resolved=True)
    task = _make_task()
    budget = BudgetProfile(wall_time_s=60, token_cap=1000, max_tool_calls=10)

    with patch("scripts.benchmark_runner.create_task_sandbox") as mock_sandbox:
        mock_sandbox.return_value = Path("/tmp/fake-sandbox")
        run_data = asyncio.run(
            run_lane(agent, "B7", [task], budget, None),
        )

    result = run_data["results"][0]
    assert "artifacts" in result
    assert result["artifacts"]["grade_attempts"][0]["attempt"] == 1


# --- Tool restriction injection ---


def test_tool_restriction_injected_into_task_extra():
    """B8 lane config tool_restriction is injected into task.extra."""
    agent = _make_agent(resolved=True)
    task = _make_task()
    budget = BudgetProfile(wall_time_s=60, token_cap=1000, max_tool_calls=10)

    # B8 has tool_restriction: "bash-only"
    assert LANE_CONFIGS["B8"]["tool_restriction"] == "bash-only"

    captured_task = None

    async def capture_solve(t: BenchmarkTask, sandbox: Path, b: BudgetProfile) -> AgentResult:
        nonlocal captured_task
        captured_task = t
        return AgentResult(task_id=t.task_id, resolved=True, wall_time_s=1.0)

    agent.solve_task = AsyncMock(side_effect=capture_solve)

    with patch("scripts.benchmark_runner.create_task_sandbox") as mock_sandbox:
        mock_sandbox.return_value = Path("/tmp/fake-sandbox")
        asyncio.run(run_lane(agent, "B8", [task], budget, None))

    assert captured_task is not None
    assert captured_task.extra["tool_restriction"] == "bash-only"


# --- Extra deps (manifest-driven) ---


def test_extra_apt_deps_installed_in_docker(tmp_path: Path):
    """extra_apt_deps in task.extra should trigger apt-get install in Docker."""
    agent = _make_agent(resolved=True)
    task = _make_task()
    task.extra["python_version"] = "3.7"
    task.extra["extra_apt_deps"] = ["libfreetype6-dev", "libpng-dev"]
    budget = BudgetProfile(wall_time_s=60, token_cap=1000, max_tool_calls=10)

    docker_exec_calls: list[str] = []

    def mock_docker_exec(name, cmd, *, timeout=300, workdir=None):
        docker_exec_calls.append(cmd)
        return MagicMock(returncode=0, stdout="ok", stderr="")

    with patch("scripts.benchmark_runner.create_task_sandbox") as mock_sandbox, \
         patch("scripts.benchmark_runner.docker_available", return_value=True), \
         patch("scripts.benchmark_runner.start_container") as mock_start, \
         patch("scripts.benchmark_runner.docker_exec", side_effect=mock_docker_exec), \
         patch("scripts.benchmark_runner.install_build_deps") as mock_deps, \
         patch("scripts.benchmark_runner.get_image_digest", return_value="sha256:test"), \
         patch("scripts.benchmark_runner.fix_permissions"), \
         patch("scripts.benchmark_runner.stop_and_remove"):
        mock_sandbox.return_value = tmp_path
        mock_start.return_value = MagicMock(returncode=0, stdout="cid", stderr="")
        mock_deps.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
        asyncio.run(run_lane(agent, "B7", [task], budget, None))

    # Find the apt-get install call for extra deps
    apt_calls = [c for c in docker_exec_calls if "libfreetype6-dev" in c]
    assert len(apt_calls) == 1
    assert "libpng-dev" in apt_calls[0]


def test_extra_pip_deps_installed_in_docker(tmp_path: Path):
    """extra_pip_deps in task.extra should trigger pip install in Docker."""
    agent = _make_agent(resolved=True)
    task = _make_task()
    task.extra["python_version"] = "3.7"
    task.extra["extra_pip_deps"] = ["Cython<3"]
    budget = BudgetProfile(wall_time_s=60, token_cap=1000, max_tool_calls=10)

    docker_exec_calls: list[str] = []

    def mock_docker_exec(name, cmd, *, timeout=300, workdir=None):
        docker_exec_calls.append(cmd)
        return MagicMock(returncode=0, stdout="ok", stderr="")

    with patch("scripts.benchmark_runner.create_task_sandbox") as mock_sandbox, \
         patch("scripts.benchmark_runner.docker_available", return_value=True), \
         patch("scripts.benchmark_runner.start_container") as mock_start, \
         patch("scripts.benchmark_runner.docker_exec", side_effect=mock_docker_exec), \
         patch("scripts.benchmark_runner.install_build_deps") as mock_deps, \
         patch("scripts.benchmark_runner.get_image_digest", return_value="sha256:test"), \
         patch("scripts.benchmark_runner.fix_permissions"), \
         patch("scripts.benchmark_runner.stop_and_remove"):
        mock_sandbox.return_value = tmp_path
        mock_start.return_value = MagicMock(returncode=0, stdout="cid", stderr="")
        mock_deps.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
        asyncio.run(run_lane(agent, "B7", [task], budget, None))

    # Find the pip install call for extra deps
    pip_calls = [c for c in docker_exec_calls if "Cython<3" in c]
    assert len(pip_calls) == 1
    assert "pip install" in pip_calls[0]


def test_extra_apt_failure_stops_setup(tmp_path: Path):
    """If extra_apt_deps install fails, setup should stop."""
    agent = _make_agent(resolved=True)
    task = _make_task()
    task.extra["python_version"] = "3.7"
    task.extra["extra_apt_deps"] = ["nonexistent-package"]
    budget = BudgetProfile(wall_time_s=60, token_cap=1000, max_tool_calls=10)

    call_count = 0

    def mock_docker_exec(name, cmd, *, timeout=300, workdir=None):
        nonlocal call_count
        call_count += 1
        if "nonexistent-package" in cmd:
            return MagicMock(returncode=1, stdout="", stderr="package not found")
        return MagicMock(returncode=0, stdout="ok", stderr="")

    with patch("scripts.benchmark_runner.create_task_sandbox") as mock_sandbox, \
         patch("scripts.benchmark_runner.docker_available", return_value=True), \
         patch("scripts.benchmark_runner.start_container") as mock_start, \
         patch("scripts.benchmark_runner.docker_exec", side_effect=mock_docker_exec), \
         patch("scripts.benchmark_runner.install_build_deps") as mock_deps, \
         patch("scripts.benchmark_runner.get_image_digest", return_value="sha256:test"), \
         patch("scripts.benchmark_runner.stop_and_remove"):
        mock_sandbox.return_value = tmp_path
        mock_start.return_value = MagicMock(returncode=0, stdout="cid", stderr="")
        mock_deps.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
        run_data = asyncio.run(run_lane(agent, "B7", [task], budget, None))

    agent.solve_task.assert_not_called()
    assert run_data["results"][0]["error"] == "Setup failed"


# --- Manifest validation ---


def test_manifest_no_tail_truncation():
    """No setup commands should have '| tail' output truncation."""
    from scripts.adapters.base import load_manifest
    manifest = PROJECT_ROOT / "scripts" / "e2e" / "external" / "swebench-pilot-subset.json"
    if not manifest.exists():
        return  # skip if no manifest
    _, tasks = load_manifest(manifest)
    for task in tasks:
        for cmd in task.setup_commands:
            assert "| tail" not in cmd, (
                f"Task {task.task_id} still has '| tail' in setup: {cmd}"
            )


def test_manifest_sklearn_has_extra_pip_deps():
    """scikit-learn tasks should have extra_pip_deps with Cython<3."""
    from scripts.adapters.base import load_manifest
    manifest = PROJECT_ROOT / "scripts" / "e2e" / "external" / "swebench-pilot-subset.json"
    if not manifest.exists():
        return
    _, tasks = load_manifest(manifest)
    sklearn_tasks = [t for t in tasks if t.task_id.startswith("scikit-learn__")]
    assert len(sklearn_tasks) > 0
    for task in sklearn_tasks:
        assert "extra_pip_deps" in task.extra, (
            f"Task {task.task_id} missing extra_pip_deps"
        )
        assert "Cython<3" in task.extra["extra_pip_deps"]


def test_manifest_matplotlib_has_extra_apt_deps():
    """matplotlib tasks should have extra_apt_deps with freetype/png."""
    from scripts.adapters.base import load_manifest
    manifest = PROJECT_ROOT / "scripts" / "e2e" / "external" / "swebench-pilot-subset.json"
    if not manifest.exists():
        return
    _, tasks = load_manifest(manifest)
    mpl_tasks = [t for t in tasks if t.task_id.startswith("matplotlib__")]
    assert len(mpl_tasks) > 0
    for task in mpl_tasks:
        assert "extra_apt_deps" in task.extra, (
            f"Task {task.task_id} missing extra_apt_deps"
        )
        assert "libfreetype6-dev" in task.extra["extra_apt_deps"]
        assert "libpng-dev" in task.extra["extra_apt_deps"]
