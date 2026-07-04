"""Tests for the verification gate and evidence system."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from autocode.agent.verification import (
    CheckResult,
    VerificationEvidence,
    VerifyResult,
    VERIFY_JSON_SCHEMA,
)


class TestCheckResult:
    def test_passed_when_exit_code_zero(self) -> None:
        check = CheckResult(name="test", command="pytest", exit_code=0)
        assert check.passed is True

    def test_failed_when_exit_code_nonzero(self) -> None:
        check = CheckResult(name="test", command="pytest", exit_code=1)
        assert check.passed is False


class TestVerifyResult:
    def test_from_json_all_passed(self) -> None:
        data = {
            "timestamp": "2026-04-03T12:00:00Z",
            "checks": [
                {"name": "lint", "command": "ruff check .", "exit_code": 0, "duration_ms": 100, "summary": "ok"},
                {"name": "test", "command": "pytest", "exit_code": 0, "duration_ms": 5000, "summary": "42 passed"},
            ],
            "all_passed": True,
            "total_duration_ms": 5100,
        }
        result = VerifyResult.from_json(data)
        assert result.all_passed is True
        assert len(result.checks) == 2
        assert result.checks[0].name == "lint"
        assert result.checks[1].passed is True
        assert result.total_duration_ms == 5100

    def test_from_json_with_failure(self) -> None:
        data = {
            "checks": [
                {"name": "test", "command": "pytest", "exit_code": 1},
            ],
            "all_passed": False,
        }
        result = VerifyResult.from_json(data)
        assert result.all_passed is False
        assert result.checks[0].passed is False

    def test_from_file(self, tmp_path: Path) -> None:
        data = {"checks": [{"name": "t", "command": "t", "exit_code": 0}], "all_passed": True}
        f = tmp_path / "verify.json"
        f.write_text(json.dumps(data))
        result = VerifyResult.from_file(f)
        assert result is not None
        assert result.all_passed is True

    def test_from_file_invalid_json(self, tmp_path: Path) -> None:
        f = tmp_path / "verify.json"
        f.write_text("not json")
        result = VerifyResult.from_file(f)
        assert result is None

    def test_from_file_missing(self, tmp_path: Path) -> None:
        result = VerifyResult.from_file(tmp_path / "missing.json")
        assert result is None

    def test_to_dict_roundtrip(self) -> None:
        data = {
            "timestamp": "2026-04-03T12:00:00Z",
            "checks": [{"name": "lint", "command": "ruff", "exit_code": 0, "duration_ms": 50, "summary": ""}],
            "all_passed": True,
            "total_duration_ms": 50,
        }
        result = VerifyResult.from_json(data)
        roundtrip = result.to_dict()
        assert roundtrip["all_passed"] is True
        assert len(roundtrip["checks"]) == 1
        assert roundtrip["checks"][0]["name"] == "lint"

    def test_empty_checks(self) -> None:
        result = VerifyResult.from_json({"checks": [], "all_passed": False})
        assert result.checks == []
        assert result.all_passed is False


class TestVerificationEvidence:
    def test_initial_state(self) -> None:
        ev = VerificationEvidence()
        assert ev.needed is False
        assert ev.satisfied is False
        assert ev.result is None

    def test_mark_needed(self) -> None:
        ev = VerificationEvidence()
        ev.mark_needed()
        assert ev.needed is True
        assert ev.satisfied is False

    def test_submit_passing_evidence(self) -> None:
        ev = VerificationEvidence()
        ev.mark_needed()
        result = VerifyResult(all_passed=True, checks=[])
        ev.submit_evidence(result)
        assert ev.satisfied is True
        assert ev.result is result

    def test_submit_failing_evidence(self) -> None:
        ev = VerificationEvidence()
        ev.mark_needed()
        result = VerifyResult(all_passed=False, checks=[])
        ev.submit_evidence(result)
        assert ev.satisfied is False

    def test_should_block_when_needed_and_unsatisfied(self) -> None:
        ev = VerificationEvidence()
        ev.mark_needed()
        assert ev.should_block_completion() is True

    def test_should_not_block_when_satisfied(self) -> None:
        ev = VerificationEvidence()
        ev.mark_needed()
        ev.submit_evidence(VerifyResult(all_passed=True, checks=[]))
        assert ev.should_block_completion() is False

    def test_should_not_block_when_not_needed(self) -> None:
        ev = VerificationEvidence()
        assert ev.should_block_completion() is False

    def test_retry_limit(self) -> None:
        ev = VerificationEvidence()
        ev.mark_needed()
        assert ev.record_retry() is True  # 1
        assert ev.record_retry() is True  # 2
        assert ev.record_retry() is True  # 3
        assert ev.record_retry() is False  # 4 — exceeded

    def test_retries_exhausted_allows_completion(self) -> None:
        ev = VerificationEvidence()
        ev.mark_needed()
        for _ in range(4):
            ev.record_retry()
        # After max retries, completion is no longer blocked
        assert ev.should_block_completion() is False


class TestVerifyJsonSchema:
    def test_schema_has_required_fields(self) -> None:
        assert "checks" in VERIFY_JSON_SCHEMA["required"]
        assert "all_passed" in VERIFY_JSON_SCHEMA["required"]
