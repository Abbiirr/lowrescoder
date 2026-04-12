"""Tests for first-run bootstrap."""

from __future__ import annotations

from autocode.packaging.bootstrap import BootstrapResult, BootstrapStep, run_bootstrap


def test_bootstrap_runs() -> None:
    """Bootstrap runs and returns a result."""
    result = run_bootstrap()
    assert isinstance(result, BootstrapResult)
    assert len(result.steps) >= 5
    assert result.platform is not None


def test_bootstrap_python_passes() -> None:
    """Python check passes (we're running 3.11+)."""
    result = run_bootstrap()
    py_step = next(s for s in result.steps if "Python" in s.name)
    assert py_step.completed


def test_bootstrap_git_passes() -> None:
    """Git check passes on this machine."""
    result = run_bootstrap()
    git_step = next(s for s in result.steps if s.name == "Git")
    assert git_step.completed


def test_bootstrap_summary() -> None:
    """Summary contains key information."""
    result = run_bootstrap()
    summary = result.summary()
    assert "AutoCode First-Run Setup" in summary
    assert "[OK]" in summary
    assert "steps complete" in summary


def test_bootstrap_step_remediation() -> None:
    """Failed steps have remediation messages."""
    step = BootstrapStep(
        name="Missing Thing",
        description="Needs fixing",
        completed=False,
        remediation="Install it: https://example.com",
    )
    assert step.remediation
    assert "Install" in step.remediation


def test_bootstrap_ready_when_required_pass() -> None:
    """Bootstrap is ready when all required steps pass."""
    result = BootstrapResult(
        steps=[
            BootstrapStep(name="req1", description="", required=True, completed=True),
            BootstrapStep(name="opt1", description="", required=False, completed=False),
        ],
        ready=True,
    )
    assert result.ready
    assert result.passed_count == 1
    assert len(result.failed_required) == 0


def test_bootstrap_includes_autocode_command_step() -> None:
    """Bootstrap reports whether the autocode command is available on PATH."""
    result = run_bootstrap()
    step = next(s for s in result.steps if s.name == "AutoCode CLI")
    assert "autocode" in step.description.lower()
    assert "PATH" in step.remediation
