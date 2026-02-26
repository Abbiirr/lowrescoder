"""Unit tests for scripts.docker_helpers — all subprocess calls mocked."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.docker_helpers import (  # noqa: E402
    docker_available,
    docker_exec,
    get_image_digest,
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


# --- docker_available ---


class TestDockerAvailable:
    @patch("scripts.docker_helpers.subprocess.run")
    def test_true_when_daemon_up(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        assert docker_available() is True
        mock_run.assert_called_once()

    @patch("scripts.docker_helpers.subprocess.run")
    def test_false_when_daemon_down(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1)
        assert docker_available() is False

    @patch("scripts.docker_helpers.subprocess.run", side_effect=FileNotFoundError)
    def test_false_when_no_cli(self, mock_run):
        assert docker_available() is False

    @patch(
        "scripts.docker_helpers.subprocess.run",
        side_effect=subprocess.TimeoutExpired("docker", 10),
    )
    def test_false_on_timeout(self, mock_run):
        assert docker_available() is False


# --- start_container ---


class TestStartContainer:
    @patch("scripts.docker_helpers.subprocess.run")
    def test_correct_command(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="abc123\n")
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

    @patch("scripts.docker_helpers.subprocess.run")
    def test_uses_correct_python_version(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        start_container("c", "3.7", "/s")
        cmd = mock_run.call_args[0][0]
        assert "python:3.7-slim" in cmd


# --- docker_exec ---


class TestDockerExec:
    @patch("scripts.docker_helpers.subprocess.run")
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

    @patch("scripts.docker_helpers.subprocess.run")
    def test_custom_workdir(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        docker_exec("myc", "ls", workdir="/work/repo")
        cmd = mock_run.call_args[0][0]
        assert "-w" in cmd
        assert "/work/repo" in cmd

    @patch("scripts.docker_helpers.subprocess.run")
    def test_timeout_forwarded(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        docker_exec("myc", "pip install -e .", timeout=600)
        assert mock_run.call_args[1]["timeout"] == 600


# --- install_build_deps ---


class TestInstallBuildDeps:
    @patch("scripts.docker_helpers.subprocess.run")
    def test_installs_packages(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        result = install_build_deps("myc")
        assert result.returncode == 0
        cmd = mock_run.call_args[0][0]
        bash_cmd = cmd[-1]
        assert "apt-get" in bash_cmd
        assert "gcc" in bash_cmd

    @patch("scripts.docker_helpers.subprocess.run")
    def test_installs_pytest(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        install_build_deps("myc")
        cmd = mock_run.call_args[0][0]
        bash_cmd = cmd[-1]
        assert "pytest" in bash_cmd

    @patch("scripts.docker_helpers.subprocess.run")
    def test_no_output_suppression(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        install_build_deps("myc")
        cmd = mock_run.call_args[0][0]
        bash_cmd = cmd[-1]
        assert ">/dev/null" not in bash_cmd


# --- stop_and_remove ---


class TestStopAndRemove:
    @patch("scripts.docker_helpers.subprocess.run")
    def test_calls_stop_and_rm(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        stop_and_remove("myc")
        calls = mock_run.call_args_list
        assert len(calls) == 2
        assert calls[0][0][0] == ["docker", "stop", "myc"]
        assert calls[1][0][0] == ["docker", "rm", "myc"]

    @patch("scripts.docker_helpers.subprocess.run", side_effect=Exception("boom"))
    def test_never_raises(self, mock_run):
        # Should not raise even if subprocess fails
        stop_and_remove("myc")

    @patch("scripts.docker_helpers.subprocess.run")
    def test_continues_after_stop_fails(self, mock_run):
        mock_run.side_effect = [Exception("stop failed"), MagicMock(returncode=0)]
        stop_and_remove("myc")  # Should not raise


# --- get_image_digest ---


class TestGetImageDigest:
    @patch("scripts.docker_helpers.subprocess.run")
    def test_returns_digest(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0, stdout="sha256:abc123\n",
        )
        digest = get_image_digest("3.9")
        assert digest == "sha256:abc123"
        cmd = mock_run.call_args[0][0]
        assert "python:3.9-slim" in cmd

    @patch("scripts.docker_helpers.subprocess.run")
    def test_returns_unknown_on_failure(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1)
        assert get_image_digest("3.9") == "unknown"

    @patch("scripts.docker_helpers.subprocess.run", side_effect=Exception("x"))
    def test_returns_unknown_on_exception(self, mock_run):
        assert get_image_digest("3.9") == "unknown"
