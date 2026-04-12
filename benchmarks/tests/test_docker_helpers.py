"""Unit tests for scripts.docker_helpers — all subprocess calls mocked."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from benchmarks.docker_helpers import (  # noqa: E402
    docker_available,
    docker_exec,
    ensure_container_name_available,
    get_image_digest,
    inspect_container_state,
    install_build_deps,
    make_container_name,
    start_container,
    stop_and_remove,
)

# --- make_container_name ---


class TestMakeContainerName:
    def test_basic(self):
        name = make_container_name("django__django-10880", "B7")
        assert name == "bench-B7-django__django-10880"

    def test_sanitizes_special_chars(self):
        name = make_container_name("foo/bar:baz", "B7")
        # slashes and colons become hyphens
        assert "/" not in name
        assert ":" not in name

    def test_starts_with_alnum(self):
        name = make_container_name("__leading", "B7")
        assert name[0].isalnum()

    def test_truncates_long_names(self):
        long_id = "a" * 200
        name = make_container_name(long_id, "B7")
        assert len(name) <= 128

    def test_unique_for_different_lanes(self):
        n1 = make_container_name("task-1", "B7")
        n2 = make_container_name("task-1", "B8")
        assert n1 != n2

    def test_unique_for_different_run_ids(self):
        n1 = make_container_name("task-1", "B7", "run-a")
        n2 = make_container_name("task-1", "B7", "run-b")
        assert n1 != n2


# --- docker_available ---


class TestDockerAvailable:
    @patch("benchmarks.docker_helpers.subprocess.run")
    def test_true_when_daemon_up(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        assert docker_available() is True
        mock_run.assert_called_once()

    @patch("benchmarks.docker_helpers.subprocess.run")
    def test_false_when_daemon_down(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1)
        assert docker_available() is False

    @patch("benchmarks.docker_helpers.subprocess.run", side_effect=FileNotFoundError)
    def test_false_when_no_cli(self, mock_run):
        assert docker_available() is False

    @patch(
        "benchmarks.docker_helpers.subprocess.run",
        side_effect=subprocess.TimeoutExpired("docker", 10),
    )
    def test_false_on_timeout(self, mock_run):
        assert docker_available() is False


# --- start_container ---


class TestStartContainer:
    @patch("benchmarks.docker_helpers.ensure_container_name_available")
    @patch("benchmarks.docker_helpers.subprocess.run")
    def test_clears_stale_same_name_container_first(
        self,
        mock_run,
        mock_ensure_available,
    ):
        mock_run.return_value = MagicMock(returncode=0, stdout="abc123\n")
        start_container("mycontainer", "3.9", "/tmp/sandbox")
        mock_ensure_available.assert_called_once_with("mycontainer")

    @patch("benchmarks.docker_helpers.subprocess.run")
    def test_correct_command(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="abc123\n")
        with patch("benchmarks.docker_helpers.ensure_container_name_available"):
            result = start_container("mycontainer", "3.9", "/tmp/sandbox")
        assert result.returncode == 0
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "docker"
        assert "run" in cmd
        assert "-d" in cmd
        assert "--name" in cmd
        assert "mycontainer" in cmd
        assert "-v" in cmd
        assert "/tmp/sandbox:/work" in cmd
        assert "python:3.9-slim" in cmd

    @patch("benchmarks.docker_helpers.subprocess.run")
    def test_uses_correct_python_version(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        with patch("benchmarks.docker_helpers.ensure_container_name_available"):
            start_container("c", "3.7", "/s")
        cmd = mock_run.call_args[0][0]
        assert "python:3.7-slim" in cmd


class TestEnsureContainerNameAvailable:
    @patch("benchmarks.docker_helpers.subprocess.run")
    def test_force_removes_existing_name(self, mock_run):
        ensure_container_name_available("myc")
        mock_run.assert_called_once_with(
            ["docker", "rm", "-f", "myc"],
            capture_output=True,
            text=True,
            timeout=30,
        )

    @patch("benchmarks.docker_helpers.subprocess.run", side_effect=Exception("boom"))
    def test_swallows_cleanup_errors(self, mock_run):
        ensure_container_name_available("myc")


# --- docker_exec ---


class TestDockerExec:
    @patch("benchmarks.docker_helpers.subprocess.run")
    def test_wraps_with_pipefail(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0, stdout="ok", stderr="",
        )
        result = docker_exec("myc", "echo hello")
        assert result.returncode == 0
        cmd = mock_run.call_args[0][0]
        assert "bash" in cmd
        assert "-c" in cmd
        # The actual command string should contain pipefail
        bash_cmd = cmd[-1]
        assert "set -o pipefail" in bash_cmd
        assert "echo hello" in bash_cmd

    @patch("benchmarks.docker_helpers.subprocess.run")
    def test_whitelists_safe_directory(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
        docker_exec("myc", "git status")
        bash_cmd = mock_run.call_args[0][0][-1]
        assert "git config --global --add safe.directory '*'" in bash_cmd

    @patch("benchmarks.docker_helpers.subprocess.run")
    def test_custom_workdir(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        docker_exec("myc", "ls", workdir="/work/repo")
        cmd = mock_run.call_args[0][0]
        assert "-w" in cmd
        assert "/work/repo" in cmd

    @patch("benchmarks.docker_helpers.subprocess.run")
    def test_timeout_forwarded(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        docker_exec("myc", "pip install -e .", timeout=600)
        assert mock_run.call_args[1]["timeout"] == 600


# --- install_build_deps ---


class TestInstallBuildDeps:
    @patch("benchmarks.docker_helpers.subprocess.run")
    def test_installs_packages(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        result = install_build_deps("myc")
        assert result.returncode == 0
        cmd = mock_run.call_args[0][0]
        bash_cmd = cmd[-1]
        assert "apt-get" in bash_cmd
        assert "gcc" in bash_cmd

    @patch("benchmarks.docker_helpers.subprocess.run")
    def test_installs_pytest(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        install_build_deps("myc")
        cmd = mock_run.call_args[0][0]
        bash_cmd = cmd[-1]
        assert "pytest" in bash_cmd

    @patch("benchmarks.docker_helpers.subprocess.run")
    def test_no_output_suppression(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        install_build_deps("myc")
        cmd = mock_run.call_args[0][0]
        bash_cmd = cmd[-1]
        install_segment = bash_cmd.split("set -o pipefail; ", 1)[-1]
        assert ">/dev/null" not in install_segment

    @patch("benchmarks.docker_helpers.subprocess.run")
    def test_full_profile_uses_longer_timeout(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        install_build_deps("myc", profile="full")
        assert mock_run.call_args[1]["timeout"] == 900

    @patch("benchmarks.docker_helpers.subprocess.run")
    def test_git_only_profile_installs_git(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        install_build_deps("myc", profile="git-only")
        bash_cmd = mock_run.call_args[0][0][-1]
        assert "apt-get install -y -qq git" in bash_cmd
        assert "python3-dev" not in bash_cmd
        assert "pytest" not in bash_cmd

    @patch("benchmarks.docker_helpers.subprocess.run")
    def test_none_profile_skips_subprocess(self, mock_run):
        result = install_build_deps("myc", profile="none")
        assert result.returncode == 0
        assert "skipped build deps" in result.stdout
        mock_run.assert_not_called()


# --- stop_and_remove ---


class TestStopAndRemove:
    @patch("benchmarks.docker_helpers.subprocess.run")
    def test_calls_stop_and_rm(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        stop_and_remove("myc")
        calls = mock_run.call_args_list
        assert len(calls) == 2
        assert calls[0][0][0] == ["docker", "stop", "myc"]
        assert calls[1][0][0] == ["docker", "rm", "myc"]

    @patch("benchmarks.docker_helpers.subprocess.run", side_effect=Exception("boom"))
    def test_never_raises(self, mock_run):
        # Should not raise even if subprocess fails
        stop_and_remove("myc")

    @patch("benchmarks.docker_helpers.subprocess.run")
    def test_continues_after_stop_fails(self, mock_run):
        mock_run.side_effect = [Exception("stop failed"), MagicMock(returncode=0)]
        stop_and_remove("myc")  # Should not raise


# --- get_image_digest ---


class TestGetImageDigest:
    @patch("benchmarks.docker_helpers.subprocess.run")
    def test_returns_digest(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0, stdout="sha256:abc123\n",
        )
        digest = get_image_digest("3.9")
        assert digest == "sha256:abc123"
        cmd = mock_run.call_args[0][0]
        assert "python:3.9-slim" in cmd

    @patch("benchmarks.docker_helpers.subprocess.run")
    def test_returns_unknown_on_failure(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1)
        assert get_image_digest("3.9") == "unknown"

    @patch("benchmarks.docker_helpers.subprocess.run", side_effect=Exception("x"))
    def test_returns_unknown_on_exception(self, mock_run):
        assert get_image_digest("3.9") == "unknown"


class TestInspectContainerState:
    @patch("benchmarks.docker_helpers.subprocess.run")
    def test_returns_state_fields(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="status=exited exit=137 oom=false error=\n",
            stderr="",
        )
        state = inspect_container_state("myc")
        assert state["container_name"] == "myc"
        assert state["status"] == "exited"
        assert state["exit_code"] == 137
        assert state["oom_killed"] is False

    @patch("benchmarks.docker_helpers.subprocess.run")
    def test_returns_inspect_error_on_failure(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="no such container",
        )
        state = inspect_container_state("missing")
        assert state["container_name"] == "missing"
        assert "inspect_error" in state
