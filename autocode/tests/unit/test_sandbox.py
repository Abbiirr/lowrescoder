"""Tests for OS-level sandboxing."""

from __future__ import annotations

import subprocess
from unittest.mock import patch

from autocode.agent.sandbox import (
    SandboxConfig,
    SandboxPolicy,
    SandboxResult,
    _run_bwrap,
    _should_fallback_from_bwrap,
    detect_sandbox_support,
    run_sandboxed,
)


def test_detect_support() -> None:
    """detect_sandbox_support returns a dict with known keys."""
    support = detect_sandbox_support()
    assert "none" in support
    assert support["none"] is True
    assert "bwrap" in support
    assert "seatbelt" in support


def test_sandbox_none_policy() -> None:
    """NONE policy runs without sandbox."""
    config = SandboxConfig(policy=SandboxPolicy.NONE, timeout_s=5)
    result = run_sandboxed("echo hello", config)
    assert "hello" in result.stdout
    assert result.sandbox_type == "none"


def test_sandbox_timeout() -> None:
    """Sandbox enforces timeout."""
    config = SandboxConfig(policy=SandboxPolicy.NONE, timeout_s=1)
    result = run_sandboxed("sleep 30", config)
    assert result.returncode != 0
    assert "imeout" in result.stderr or result.returncode == 124


def test_sandbox_result_structure() -> None:
    """SandboxResult has expected fields."""
    result = SandboxResult(
        stdout="out", stderr="err", returncode=0,
        sandbox_type="bwrap", enforced=True,
    )
    assert result.enforced
    assert result.sandbox_type == "bwrap"


def test_sandbox_captures_output() -> None:
    """Sandbox captures stdout and stderr."""
    config = SandboxConfig(policy=SandboxPolicy.NONE, timeout_s=5)
    result = run_sandboxed("echo out && echo err >&2", config)
    assert "out" in result.stdout
    assert "err" in result.stderr


def test_bwrap_permission_error_falls_back_to_restricted_env() -> None:
    """bwrap permission/setup failures degrade to restricted-env execution."""
    config = SandboxConfig(
        policy=SandboxPolicy.WRITABLE_PROJECT,
        timeout_s=5,
        project_root=".",
    )

    def fake_run(*args, **kwargs):  # type: ignore[no-untyped-def]
        cmd = args[0]
        if isinstance(cmd, list) and cmd and cmd[0] == "bwrap":
            return subprocess.CompletedProcess(
                cmd,
                1,
                stdout="",
                stderr="bwrap: setting up uid map: Permission denied",
            )
        return subprocess.CompletedProcess(
            cmd,
            0,
            stdout="fallback ok\n",
            stderr="",
        )

    with patch("autocode.agent.sandbox.subprocess.run", side_effect=fake_run):
        result = _run_bwrap("echo fallback ok", config)

    assert result.returncode == 0
    assert result.stdout == "fallback ok\n"
    assert result.sandbox_type == "restricted_env"
    assert result.enforced is False


def test_should_fallback_from_bwrap_matches_uid_map_error() -> None:
    """Known namespace/uid-map failures should trigger bwrap fallback."""
    assert _should_fallback_from_bwrap(
        "bwrap: setting up uid map: Permission denied",
    )
    assert _should_fallback_from_bwrap(
        "bwrap: No permissions to create new namespace",
    )
    assert not _should_fallback_from_bwrap("plain command failure")
