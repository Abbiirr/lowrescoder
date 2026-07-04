"""Tests for the artifact collector."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from autocode.agent.artifact_collector import ArtifactCollector


class TestArtifactCollector:
    def test_log_command(self, tmp_path: Path) -> None:
        collector = ArtifactCollector("test-session", tmp_path)
        collector.log_command("pytest", exit_code=0, duration_ms=100, tool_name="run_command")
        collector.log_command("ruff check .", exit_code=1, duration_ms=50, tool_name="run_command")
        assert len(collector._commands) == 2
        assert collector._commands[0].exit_code == 0
        assert collector._commands[1].exit_code == 1

    def test_save_commands_log(self, tmp_path: Path) -> None:
        collector = ArtifactCollector("test-session", tmp_path)
        collector.log_command("pytest -v", exit_code=0, duration_ms=5000)
        collector.log_command("ruff check .", exit_code=1, duration_ms=200)
        path = collector.save_commands_log()
        assert path.exists()
        content = path.read_text()
        assert "pytest -v" in content
        assert "OK" in content
        assert "FAIL(1)" in content

    def test_save_verify_json(self, tmp_path: Path) -> None:
        collector = ArtifactCollector("test-session", tmp_path)
        data = {"checks": [{"name": "test", "exit_code": 0}], "all_passed": True}
        path = collector.save_verify_json(data)
        assert path.exists()
        loaded = json.loads(path.read_text())
        assert loaded["all_passed"] is True

    def test_generate_risk_summary_low_risk(self, tmp_path: Path) -> None:
        collector = ArtifactCollector("test-session", tmp_path)
        collector.log_command("pytest", exit_code=0, duration_ms=100)
        summary = collector.generate_risk_summary(verify_passed=True)
        assert "LOW" in summary
        assert "GO" in summary

    def test_generate_risk_summary_high_risk_verification_failed(self, tmp_path: Path) -> None:
        collector = ArtifactCollector("test-session", tmp_path)
        for i in range(10):
            collector.log_command(f"cmd-{i}", exit_code=1, duration_ms=10)
        summary = collector.generate_risk_summary(verify_passed=False)
        assert "HIGH" in summary
        assert "NO-GO" in summary

    def test_save_risk_summary(self, tmp_path: Path) -> None:
        collector = ArtifactCollector("test-session", tmp_path)
        path = collector.save_risk_summary(verify_passed=True)
        assert path.exists()
        assert "Risk Summary" in path.read_text()

    def test_log_file_change(self, tmp_path: Path) -> None:
        collector = ArtifactCollector("test-session", tmp_path)
        collector.log_file_change("src/main.py")
        collector.log_file_change("src/utils.py")
        collector.log_file_change("src/main.py")  # duplicate
        assert len(collector._files_changed) == 2

    def test_artifact_dir_structure(self, tmp_path: Path) -> None:
        collector = ArtifactCollector("my-session-123", tmp_path)
        collector.ensure_dir()
        expected = tmp_path / ".autocode" / "artifacts" / "my-session-123"
        assert expected.is_dir()
