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

from scripts.benchmark_runner import (  # noqa: E402  # isort: skip
    LANE_CONFIGS,
    build_run_contract,
    run_lane,
)


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


def test_run_lane_passes_build_deps_profile_from_task_extra(tmp_path: Path):
    """Docker setup should honor per-task build_deps_profile."""
    agent = _make_agent(resolved=True)
    task = _make_task()
    task.extra["python_version"] = "3.11"
    task.extra["build_deps_profile"] = "none"
    budget = BudgetProfile(wall_time_s=60, token_cap=1000, max_tool_calls=10)

    with patch("scripts.benchmark_runner.create_task_sandbox") as mock_sandbox, \
         patch("scripts.benchmark_runner.docker_available", return_value=True), \
         patch("scripts.benchmark_runner.start_container") as mock_start, \
         patch("scripts.benchmark_runner.install_build_deps") as mock_deps, \
         patch("scripts.benchmark_runner.get_image_digest", return_value="sha256:test"), \
         patch("scripts.benchmark_runner.fix_permissions"), \
         patch("scripts.benchmark_runner.stop_and_remove"):
        mock_sandbox.return_value = tmp_path
        mock_start.return_value = MagicMock(returncode=0, stdout="cid", stderr="")
        mock_deps.return_value = MagicMock(returncode=0, stdout="skipped", stderr="")
        asyncio.run(run_lane(agent, "B9-PROXY", [task], budget, None))

    mock_deps.assert_called_once_with(
        "bench-B9-PROXY-test-task-adhoc-run",
        profile="none",
    )


def test_run_lane_counts_infra_from_failure_type_not_error():
    """REQUEST_TIMEOUT should not increment infra_fails just because error is set."""
    agent = _make_agent(resolved=False)
    agent.solve_task = AsyncMock(return_value=AgentResult(
        task_id="test-task",
        resolved=False,
        wall_time_s=1.0,
        error="request timed out",
        artifacts={
            "failure_type": "REQUEST_TIMEOUT",
            "failure_evidence": {"timeout_source": "request_timeout"},
        },
    ))
    task = _make_task()
    budget = BudgetProfile(wall_time_s=60, token_cap=1000, max_tool_calls=10)

    with patch("scripts.benchmark_runner.create_task_sandbox") as mock_sandbox:
        mock_sandbox.return_value = Path("/tmp/fake-sandbox")
        run_data = asyncio.run(run_lane(agent, "B7", [task], budget, None))

    assert run_data["aggregate"]["infra_fails"] == 0
    assert run_data["results"][0]["artifacts"]["failure_type"] == "REQUEST_TIMEOUT"


def test_run_lane_calls_adapter_pre_task_healthcheck():
    """Runner should delegate provider preflight to the adapter."""
    agent = _make_agent(resolved=True)
    task = _make_task()
    budget = BudgetProfile(wall_time_s=60, token_cap=1000, max_tool_calls=10)

    with patch("scripts.benchmark_runner.create_task_sandbox") as mock_sandbox:
        mock_sandbox.return_value = Path("/tmp/fake-sandbox")
        asyncio.run(run_lane(agent, "B7", [task], budget, None))

    agent.pre_task_healthcheck.assert_called_once()


def test_run_lane_halts_on_provider_healthcheck_failure():
    """A provider health failure should halt the run before solve_task."""
    from scripts.adapters.base import ProviderHealthError

    agent = _make_agent(resolved=True)
    agent.pre_task_healthcheck.side_effect = ProviderHealthError("provider down")
    task = _make_task()
    budget = BudgetProfile(wall_time_s=60, token_cap=1000, max_tool_calls=10)

    run_data = asyncio.run(run_lane(agent, "B7", [task], budget, None))

    agent.solve_task.assert_not_called()
    assert run_data["halted"] is True
    assert run_data["results"] == []


def test_run_lane_parallel_run_ids_keep_disjoint_containers_progress_and_cleanup(
    tmp_path: Path,
):
    """Concurrent runs with different run_ids should not share names or progress."""
    agent_a = _make_agent(resolved=True)
    agent_b = _make_agent(resolved=True)
    task_a = _make_task()
    task_b = _make_task()
    task_a.extra["python_version"] = "3.11"
    task_b.extra["python_version"] = "3.11"
    budget = BudgetProfile(wall_time_s=60, token_cap=1000, max_tool_calls=10)

    save_calls: list[tuple[str, str, str]] = []
    cleanup_names: list[str] = []

    def _record_progress(
        lane: str,
        agent_name: str,
        run_id: str,
        model: str,
        started_at: str,
        results: list[dict],
        image_digests: dict[str, str],
    ) -> None:
        del model, started_at, results, image_digests
        save_calls.append((lane, agent_name, run_id))

    async def _run_both() -> None:
        with patch("scripts.benchmark_runner.create_task_sandbox") as mock_sandbox, \
             patch("scripts.benchmark_runner.docker_available", return_value=True), \
             patch("scripts.benchmark_runner.start_container") as mock_start, \
             patch("scripts.benchmark_runner.install_build_deps") as mock_deps, \
             patch("scripts.benchmark_runner.fix_permissions"), \
             patch("scripts.benchmark_runner.stop_and_remove", side_effect=cleanup_names.append), \
             patch(
                 "scripts.benchmark_runner._save_progress",
                 side_effect=_record_progress,
             ):
            (tmp_path / "run-a").mkdir()
            (tmp_path / "run-b").mkdir()
            mock_sandbox.side_effect = [tmp_path / "run-a", tmp_path / "run-b"]
            mock_start.return_value = MagicMock(returncode=0, stdout="cid", stderr="")
            mock_deps.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
            await asyncio.gather(
                run_lane(
                    agent_a,
                    "B7",
                    [task_a],
                    budget,
                    None,
                    run_id="run-a",
                    started_at="2026-03-10T00:00:00+00:00",
                ),
                run_lane(
                    agent_b,
                    "B7",
                    [task_b],
                    budget,
                    None,
                    run_id="run-b",
                    started_at="2026-03-10T00:00:00+00:00",
                ),
            )
            container_names = [
                call.args[0] for call in mock_start.call_args_list
            ]
            assert len(container_names) == 2
            assert container_names[0] != container_names[1]

    asyncio.run(_run_both())

    assert sorted(save_calls) == [
        ("B7", "test-agent", "run-a"),
        ("B7", "test-agent", "run-b"),
    ]
    assert sorted(cleanup_names) == sorted(set(cleanup_names))
    assert len(cleanup_names) == 2


def test_build_run_contract_includes_run_id():
    """Artifacts should record run_id in the contract."""
    agent = _make_agent()
    budget = BudgetProfile(wall_time_s=60, token_cap=1000, max_tool_calls=10)
    contract = build_run_contract(
        agent,
        "B7",
        None,
        budget,
        "python scripts/benchmark_runner.py",
        "run-123",
    )
    assert contract["run_id"] == "run-123"


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
