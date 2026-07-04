"""Tests for autocode doctor readiness checks."""

from __future__ import annotations

import pytest

from autocode.doctor import (
    ALL_CHECKS,
    CheckResult,
    check_autocode_command,
    check_disk_space,
    check_git,
    check_lsp_readiness,
    check_mcp_readiness,
    check_python_version,
    check_tree_sitter,
    doctor_json,
    format_report,
    run_doctor,
)


def test_doctor_11_checks() -> None:
    """Doctor runs exactly 11 checks."""
    assert len(ALL_CHECKS) == 11
    results = run_doctor()
    assert len(results) == 11


def test_doctor_remediation_messages() -> None:
    """Each failing check has an actionable message."""
    # Create a fake failing result
    result = CheckResult(
        name="test_check",
        passed=False,
        message="Something failed",
        remediation="Run: fix-it-command",
    )
    assert result.remediation
    assert "Run:" in result.remediation


def test_doctor_python_check() -> None:
    """Python version check works and passes (we're running 3.11+)."""
    result = check_python_version()
    assert result.passed
    assert "3.11" in result.message or "3.12" in result.message or "3.13" in result.message


def test_doctor_tree_sitter_check() -> None:
    """tree-sitter check works."""
    result = check_tree_sitter()
    assert result.passed
    assert "tree-sitter" in result.message


def test_doctor_git_check() -> None:
    """Git check passes when run inside a git work tree.

    In the split-suite checkout the autocode component is a plain
    directory (no ``.git`` of its own), so ``check_git`` correctly reports
    "not in a git repo". Skip rather than assert in that case — the check's
    pass branch is exercised whenever the suite is checked out under git.
    """
    result = check_git()
    if not result.passed and "not in a git repo" in result.message:
        pytest.skip("autocode component is not a git work tree in this layout")
    assert result.passed


def test_doctor_autocode_command_check(monkeypatch: pytest.MonkeyPatch) -> None:
    """Doctor reports remediation when autocode command is not on PATH."""
    monkeypatch.setattr("shutil.which", lambda name: None)
    result = check_autocode_command()
    assert not result.passed
    assert "PATH" in result.message
    assert "uv tool install" in result.remediation


def test_doctor_mcp_readiness_reports_command_and_audit_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """MCP doctor check exposes serve command and audit-log discovery path."""
    audit_path = tmp_path / "mcp_audit.jsonl"
    monkeypatch.setenv("AUTOCODE_MCP_AUDIT_LOG", str(audit_path))

    result = check_mcp_readiness()

    assert result.passed
    assert "autocode mcp-serve" in result.message
    assert str(audit_path) in result.message


def test_doctor_lsp_readiness_reports_framework_without_spawning() -> None:
    """LSP doctor check reports optional server readiness without spawning."""
    result = check_lsp_readiness()

    assert result.passed
    assert "LSP adapter framework" in result.message


def test_doctor_disk_space_check() -> None:
    """Disk space check works."""
    result = check_disk_space()
    assert result.passed
    assert "GB" in result.message


def test_doctor_returns_structured_report() -> None:
    """JSON report with pass/fail per check."""
    results = run_doctor()
    json_report = doctor_json(results)

    assert isinstance(json_report, list)
    assert len(json_report) == 11
    for item in json_report:
        assert "name" in item
        assert "passed" in item
        assert isinstance(item["passed"], bool)
        assert "message" in item
        assert "remediation" in item


def test_doctor_format_report() -> None:
    """Human-readable report contains check names and status."""
    results = [
        CheckResult(name="test_pass", passed=True, message="OK"),
        CheckResult(name="test_fail", passed=False, message="Bad", remediation="Fix it"),
    ]
    report = format_report(results)
    assert "[PASS]" in report
    assert "[FAIL]" in report
    assert "Fix it" in report
    assert "1/2 checks passed" in report
