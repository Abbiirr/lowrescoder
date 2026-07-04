"""HFIX AI Verification Harness — Structured trace, typed assertions, and artifact tests.

Tests for HFIX-1 through HFIX-4:
  - Structured tool events validate and parse correctly
  - Secret scrubbing before args hashing
  - Trajectory grading (exact, in-order, any-order, family, forbidden)
  - Artifact grading (non-empty diff, must-change, must-not-change, must-contain)
  - Infrastructure classification (empty turn, 429, timeout, sandbox failure)
  - Run artifacts (tool_calls.jsonl, trajectory_report.json, run_summary.json)
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


# ---------------------------------------------------------------------------
# HFIX-1: Structured trace contract
# ---------------------------------------------------------------------------


class TestStructuredToolEvents:
    def test_tool_call_completed_validates(self):
        from autocode.backend.headless_schema import validate_event

        event = validate_event({
            "protocol_version": "0.2.0-harness",
            "type": "tool_call_completed",
            "thread_id": "t1",
            "turn_id": "tu1",
            "item_id": "item-1",
            "tool_call_id": "call-1",
            "tool_name": "search_text",
            "tool_family": "search",
            "status": "success",
            "started_at": "2026-05-01T00:00:00Z",
            "finished_at": "2026-05-01T00:00:01Z",
            "duration_ms": 1000,
            "result_bytes": 2048,
        })
        assert event.type == "tool_call_completed"
        assert event.tool_name == "search_text"
        assert event.tool_family == "search"
        assert event.status == "success"

    def test_tool_call_started_validates(self):
        from autocode.backend.headless_schema import validate_event

        event = validate_event({
            "protocol_version": "0.2.0-harness",
            "type": "tool_call_started",
            "thread_id": "t1",
            "turn_id": "tu1",
            "item_id": "item-1",
            "tool_call_id": "call-1",
            "tool_name": "edit_file",
            "tool_family": "file_write",
            "started_at": "2026-05-01T00:00:00Z",
        })
        assert event.type == "tool_call_started"
        assert event.tool_name == "edit_file"

    def test_tool_call_failed_validates(self):
        from autocode.backend.headless_schema import validate_event

        event = validate_event({
            "protocol_version": "0.2.0-harness",
            "type": "tool_call_failed",
            "thread_id": "t1",
            "turn_id": "tu1",
            "item_id": "item-1",
            "tool_call_id": "call-1",
            "tool_name": "run_command",
            "tool_family": "shell",
            "started_at": "2026-05-01T00:00:00Z",
            "finished_at": "2026-05-01T00:00:01Z",
            "error_type": "TimeoutError",
            "error_message": "command timed out",
        })
        assert event.type == "tool_call_failed"
        assert event.error_type == "TimeoutError"

    def test_malformed_tool_event_rejected(self):
        from autocode.backend.headless_schema import validate_event

        with pytest.raises(Exception):
            validate_event({
                "protocol_version": "0.2.0-harness",
                "type": "tool_call_completed",
                "status": "invalid_status_value",
            })

    def test_unknown_event_type_rejected(self):
        from autocode.backend.headless_schema import validate_event

        with pytest.raises(ValueError, match="Unknown event type"):
            validate_event({
                "protocol_version": "0.2.0-harness",
                "type": "nonexistent_event",
            })

    def test_protocol_version_bumped(self):
        from autocode.backend.headless_schema import PROTOCOL_VERSION

        assert PROTOCOL_VERSION == "0.2.0-harness"

    def test_tool_family_mapping(self):
        from autocode.backend.headless_schema import tool_family

        assert tool_family("search_text") == "search"
        assert tool_family("edit_file") == "file_write"
        assert tool_family("run_command") == "shell"
        assert tool_family("unknown_tool") == "unknown"


class TestBuildRunResultCountsTypedToolEvents:
    def test_counts_typed_tool_events(self):
        from benchmarks.ai_verification.ndjson_runner import build_run_result

        raw_lines = [
            json.dumps({"type": "thread_started", "protocol_version": "0.2.0-harness"}),
            json.dumps({"type": "tool_call_completed", "protocol_version": "0.2.0-harness", "tool_name": "edit_file", "tool_family": "file_write", "status": "success", "tool_call_id": "call-1", "started_at": "2026-05-01T00:00:00Z", "finished_at": "2026-05-01T00:00:01Z"}),
            json.dumps({"type": "tool_call_completed", "protocol_version": "0.2.0-harness", "tool_name": "search_text", "tool_family": "search", "status": "success", "tool_call_id": "call-2", "started_at": "2026-05-01T00:00:02Z", "finished_at": "2026-05-01T00:00:03Z"}),
        ]
        result = build_run_result(raw_lines, exit_code=0)
        assert result.tool_calls == 2

    def test_counts_legacy_tool_execution_events(self):
        from benchmarks.ai_verification.ndjson_runner import build_run_result

        raw_lines = [
            json.dumps({"type": "thread_started", "protocol_version": "0.2.0-harness"}),
            json.dumps({"type": "item_started", "protocol_version": "0.2.0-harness", "kind": "tool_execution"}),
            json.dumps({"type": "item_completed", "protocol_version": "0.2.0-harness"}),
        ]
        result = build_run_result(raw_lines, exit_code=0)
        assert result.tool_calls == 1

    def test_counts_mixed_typed_and_legacy_deduped(self):
        from benchmarks.ai_verification.ndjson_runner import build_run_result

        raw_lines = [
            json.dumps({"type": "item_started", "protocol_version": "0.2.0-harness", "kind": "tool_execution", "item_id": "item-1"}),
            json.dumps({"type": "item_completed", "protocol_version": "0.2.0-harness", "item_id": "item-1"}),
            json.dumps({"type": "tool_call_completed", "protocol_version": "0.2.0-harness", "tool_name": "read_file", "tool_family": "file_read", "status": "success", "tool_call_id": "call-1", "item_id": "item-1", "started_at": "2026-05-01T00:00:00Z", "finished_at": "2026-05-01T00:00:01Z"}),
        ]
        result = build_run_result(raw_lines, exit_code=0)
        assert result.tool_calls == 1

    def test_counts_tool_call_failed(self):
        from benchmarks.ai_verification.ndjson_runner import build_run_result

        raw_lines = [
            json.dumps({"type": "tool_call_failed", "protocol_version": "0.2.0-harness", "tool_name": "run_command", "tool_family": "shell", "error_type": "TimeoutError", "tool_call_id": "call-1", "started_at": "2026-05-01T00:00:00Z", "finished_at": "2026-05-01T00:00:01Z"}),
        ]
        result = build_run_result(raw_lines, exit_code=1)
        assert result.tool_calls == 1


# ---------------------------------------------------------------------------
# HFIX-1: Secret scrubbing
# ---------------------------------------------------------------------------


class TestSecretScrubbing:
    def test_scrubs_api_key(self):
        from benchmarks.ai_verification.run_artifacts import _scrub_secrets

        result = _scrub_secrets({"api_key": "sk-secret123", "name": "test"})
        assert result["api_key"] == "<redacted>"
        assert result["name"] == "test"

    def test_scrubs_nested_secrets(self):
        from benchmarks.ai_verification.run_artifacts import _scrub_secrets

        result = _scrub_secrets({"config": {"token": "abc", "count": 5}})
        assert result["config"]["token"] == "<redacted>"
        assert result["config"]["count"] == 5

    def test_scrubs_all_known_patterns(self):
        from benchmarks.ai_verification.run_artifacts import _scrub_secrets

        sample_keys = [
            "api_key", "token", "secret", "password", "authorization",
            "gateway_url", "litellm_master_key", "openrouter_api_key",
            "anthropic_api_key", "openai_api_key", "access_token",
            "refreshToken", "github_token",
        ]
        data = {k: "secret-value" for k in sample_keys}
        result = _scrub_secrets(data)
        for k in sample_keys:
            assert result[k] == "<redacted>", f"Key {k} not scrubbed"

    def test_args_sha256_uses_scrubbed_data(self):
        from benchmarks.ai_verification.run_artifacts import _sha256_hex_dict

        hash1 = _sha256_hex_dict({"api_key": "secret1", "query": "test"})
        hash2 = _sha256_hex_dict({"api_key": "secret2", "query": "test"})
        assert hash1 == hash2, "Different secret values should produce same hash after scrubbing"


# ---------------------------------------------------------------------------
# HFIX-1: tool_calls.jsonl writer
# ---------------------------------------------------------------------------


class TestToolCallsJsonlWriter:
    def test_writes_tool_calls_jsonl(self, tmp_path: Path):
        from benchmarks.ai_verification.run_artifacts import write_tool_calls_jsonl

        records = [
            {"tool_name": "edit_file", "tool_family": "file_write", "status": "success"},
            {"tool_name": "run_command", "tool_family": "shell", "status": "error"},
        ]
        path = tmp_path / "tool_calls.jsonl"
        write_tool_calls_jsonl(records, path)
        lines = path.read_text().strip().splitlines()
        assert len(lines) == 2
        assert json.loads(lines[0])["tool_name"] == "edit_file"
        assert json.loads(lines[1])["tool_name"] == "run_command"

    def test_empty_records_produces_empty_file(self, tmp_path: Path):
        from benchmarks.ai_verification.run_artifacts import write_tool_calls_jsonl

        path = tmp_path / "tool_calls.jsonl"
        write_tool_calls_jsonl([], path)
        assert path.read_text() == ""

    def test_build_tool_call_record_structure(self):
        from benchmarks.ai_verification.run_artifacts import build_tool_call_record

        record = build_tool_call_record(
            event_type="tool_call_completed",
            thread_id="t1",
            turn_id="tu1",
            item_id="item-1",
            tool_call_id="call-1",
            tool_name="search_text",
            tool_family="search",
            status="success",
            started_at="2026-05-01T00:00:00Z",
            finished_at="2026-05-01T00:00:01Z",
            duration_ms=1000,
            args={"pattern": "TODO", "path": "/src"},
            result="Found 3 matches",
        )
        assert record["tool_name"] == "search_text"
        assert record["args_sha256"] != ""
        assert record["result_bytes"] > 0
        assert record["result_preview"] == ""


# ---------------------------------------------------------------------------
# HFIX-2: Trajectory grading
# ---------------------------------------------------------------------------


class TestTrajectoryGrading:
    def _make_tool_calls(self, *names_families):
        return [
            {"tool_name": n, "tool_family": f, "status": "success"}
            for n, f in names_families
        ]

    def test_must_use_tools_passes(self):
        from benchmarks.ai_verification.trajectory_grader import grade_trajectory

        calls = self._make_tool_calls(("search_text", "search"), ("edit_file", "file_write"))
        report = grade_trajectory(calls, {"must_use_tools": ["search_text"]})
        assert report.passed

    def test_must_use_tools_fails_missing(self):
        from benchmarks.ai_verification.trajectory_grader import grade_trajectory

        calls = self._make_tool_calls(("edit_file", "file_write"))
        report = grade_trajectory(calls, {"must_use_tools": ["search_text"]})
        assert not report.passed

    def test_must_use_edit_file_accepts_file_write_family_equivalent(self):
        from benchmarks.ai_verification.trajectory_grader import grade_trajectory

        calls = self._make_tool_calls(("write_file", "file_write"))
        report = grade_trajectory(calls, {"must_use_tools": ["edit_file"]})
        assert report.passed

    def test_must_not_use_tools_passes(self):
        from benchmarks.ai_verification.trajectory_grader import grade_trajectory

        calls = self._make_tool_calls(("read_file", "file_read"))
        report = grade_trajectory(calls, {"must_not_use_tools": ["write_file"]})
        assert report.passed

    def test_must_not_use_tools_fails(self):
        from benchmarks.ai_verification.trajectory_grader import grade_trajectory

        calls = self._make_tool_calls(("write_file", "file_write"))
        report = grade_trajectory(calls, {"must_not_use_tools": ["write_file"]})
        assert not report.passed

    def test_in_order_tools_passes(self):
        from benchmarks.ai_verification.trajectory_grader import grade_trajectory

        calls = self._make_tool_calls(
            ("git_status", "git"), ("git_diff", "git"), ("edit_file", "file_write")
        )
        report = grade_trajectory(calls, {"in_order_tools": ["git_status", "git_diff"]})
        assert report.passed

    def test_in_order_tools_fails_wrong_order(self):
        from benchmarks.ai_verification.trajectory_grader import grade_trajectory

        calls = self._make_tool_calls(
            ("git_diff", "git"), ("git_status", "git")
        )
        report = grade_trajectory(calls, {"in_order_tools": ["git_status", "git_diff"]})
        assert not report.passed

    def test_any_order_tools_passes(self):
        from benchmarks.ai_verification.trajectory_grader import grade_trajectory

        calls = self._make_tool_calls(
            ("edit_file", "file_write"), ("read_file", "file_read")
        )
        report = grade_trajectory(calls, {"any_order_tools": ["read_file", "edit_file"]})
        assert report.passed

    def test_any_order_tools_fails_missing(self):
        from benchmarks.ai_verification.trajectory_grader import grade_trajectory

        calls = self._make_tool_calls(("read_file", "file_read"))
        report = grade_trajectory(calls, {"any_order_tools": ["read_file", "edit_file"]})
        assert not report.passed

    def test_must_use_tool_families_passes(self):
        from benchmarks.ai_verification.trajectory_grader import grade_trajectory

        calls = self._make_tool_calls(("search_text", "search"), ("run_command", "shell"))
        report = grade_trajectory(calls, {"must_use_tool_families": ["search", "shell"]})
        assert report.passed

    def test_must_use_tool_families_fails(self):
        from benchmarks.ai_verification.trajectory_grader import grade_trajectory

        calls = self._make_tool_calls(("read_file", "file_read"))
        report = grade_trajectory(calls, {"must_use_tool_families": ["search"]})
        assert not report.passed

    def test_exact_tools_passes(self):
        from benchmarks.ai_verification.trajectory_grader import grade_trajectory

        calls = self._make_tool_calls(("read_file", "file_read"), ("edit_file", "file_write"))
        report = grade_trajectory(calls, {"exact_tools": ["read_file", "edit_file"]})
        assert report.passed

    def test_exact_tools_fails_extra_tools(self):
        from benchmarks.ai_verification.trajectory_grader import grade_trajectory

        calls = self._make_tool_calls(
            ("read_file", "file_read"), ("edit_file", "file_write"), ("run_command", "shell")
        )
        report = grade_trajectory(calls, {"exact_tools": ["read_file", "edit_file"]})
        assert not report.passed

    def test_min_tool_calls_passes(self):
        from benchmarks.ai_verification.trajectory_grader import grade_trajectory

        calls = self._make_tool_calls(("read_file", "file_read"), ("edit_file", "file_write"))
        report = grade_trajectory(calls, {"min_tool_calls": 2})
        assert report.passed

    def test_min_tool_calls_fails(self):
        from benchmarks.ai_verification.trajectory_grader import grade_trajectory

        calls = self._make_tool_calls(("read_file", "file_read"))
        report = grade_trajectory(calls, {"min_tool_calls": 3})
        assert not report.passed

    def test_max_failed_tool_calls_passes(self):
        from benchmarks.ai_verification.trajectory_grader import grade_trajectory

        calls = [
            {"tool_name": "edit_file", "tool_family": "file_write", "status": "success"},
            {"tool_name": "run_command", "tool_family": "shell", "status": "error"},
        ]
        report = grade_trajectory(calls, {"max_failed_tool_calls": 2})
        assert report.passed

    def test_max_failed_tool_calls_fails(self):
        from benchmarks.ai_verification.trajectory_grader import grade_trajectory

        calls = [
            {"tool_name": "run_command", "tool_family": "shell", "status": "error"},
            {"tool_name": "edit_file", "tool_family": "file_write", "status": "error"},
            {"tool_name": "edit_file", "tool_family": "file_write", "status": "error"},
        ]
        report = grade_trajectory(calls, {"max_failed_tool_calls": 2})
        assert not report.passed

    def test_max_tool_calls_by_name_flags_repetition(self):
        from benchmarks.ai_verification.trajectory_grader import grade_trajectory

        calls = [
            {"tool_name": "run_command", "tool_family": "shell", "status": "success"},
            {"tool_name": "run_command", "tool_family": "shell", "status": "success"},
            {"tool_name": "run_command", "tool_family": "shell", "status": "success"},
        ]

        report = grade_trajectory(calls, {"max_tool_calls_by_name": {"run_command": 2}})

        assert not report.passed
        assert report.failures[0].assertion == "max_tool_calls_by_name(run_command)"


# ---------------------------------------------------------------------------
# HFIX-2: Turn grading
# ---------------------------------------------------------------------------


class TestTurnGrading:
    def test_no_regression_after_pass_ignores_scripted_scope_expansion(self):
        from benchmarks.ai_verification.turn_grader import grade_turns

        turns = [
            {"turn": 1, "grading_passed": True},
            {"turn": 2, "grading_passed": False, "scope_changed_after_pass": True},
            {"turn": 3, "grading_passed": True},
        ]

        report = grade_turns(
            turn_count=3,
            turns=turns,
            assertions={"no_regression_after_pass": True},
        )

        assert report.passed

    def test_no_regression_after_pass_still_fails_true_regression(self):
        from benchmarks.ai_verification.turn_grader import grade_turns

        turns = [
            {"turn": 1, "grading_passed": True},
            {"turn": 2, "grading_passed": False},
        ]

        report = grade_turns(
            turn_count=2,
            turns=turns,
            assertions={"no_regression_after_pass": True},
        )

        assert not report.passed

    def test_no_regression_after_pass_fails_when_no_turn_passed(self):
        from benchmarks.ai_verification.turn_grader import grade_turns

        turns = [
            {"turn": 1, "grading_passed": False},
            {"turn": 2, "grading_passed": False},
        ]

        report = grade_turns(
            turn_count=2,
            turns=turns,
            assertions={"no_regression_after_pass": True},
        )

        assert not report.passed
        assert report.failures[0].detail == "no passing turn observed"

    def test_require_at_least_one_passing_turn_fails_when_absent(self):
        from benchmarks.ai_verification.turn_grader import grade_turns

        report = grade_turns(
            turn_count=1,
            turns=[{"turn": 1, "grading_passed": False}],
            assertions={"require_at_least_one_passing_turn": True},
        )

        assert not report.passed
        assert report.failures[0].assertion == "require_at_least_one_passing_turn"


# ---------------------------------------------------------------------------
# HFIX-2: Artifact grading
# ---------------------------------------------------------------------------


class TestArtifactGrading:
    def test_require_non_empty_diff_passes(self):
        from benchmarks.ai_verification.artifact_grader import grade_artifacts

        report = grade_artifacts(
            diff_patch="diff --git a/file.py b/file.py\n+new line\n",
            changed_files=["file.py"],
            assertions={"require_non_empty_diff": True},
        )
        assert report.passed

    def test_require_non_empty_diff_fails_empty(self):
        from benchmarks.ai_verification.artifact_grader import grade_artifacts

        report = grade_artifacts(
            diff_patch="(no changes from seed commit)",
            changed_files=[],
            assertions={"require_non_empty_diff": True},
        )
        assert not report.passed

    def test_forbid_noop_pass_fails_no_changes(self):
        from benchmarks.ai_verification.artifact_grader import grade_artifacts

        report = grade_artifacts(
            diff_patch="",
            changed_files=[],
            assertions={"forbid_noop_pass": True},
        )
        assert not report.passed

    def test_must_change_files_passes(self):
        from benchmarks.ai_verification.artifact_grader import grade_artifacts

        report = grade_artifacts(
            diff_patch="",
            changed_files=["config.py", "utils.py"],
            assertions={"must_change_files": ["config.py"]},
        )
        assert report.passed

    def test_must_change_files_fails_missing(self):
        from benchmarks.ai_verification.artifact_grader import grade_artifacts

        report = grade_artifacts(
            diff_patch="",
            changed_files=["utils.py"],
            assertions={"must_change_files": ["config.py"]},
        )
        assert not report.passed

    def test_must_not_change_files_passes(self):
        from benchmarks.ai_verification.artifact_grader import grade_artifacts

        report = grade_artifacts(
            diff_patch="",
            changed_files=["config.py"],
            assertions={"must_not_change_files": ["test_pipeline.py"]},
        )
        assert report.passed

    def test_must_not_change_files_fails(self):
        from benchmarks.ai_verification.artifact_grader import grade_artifacts

        report = grade_artifacts(
            diff_patch="",
            changed_files=["test_pipeline.py", "config.py"],
            assertions={"must_not_change_files": ["test_pipeline.py"]},
        )
        assert not report.passed

    def test_must_contain_text(self, tmp_path: Path):
        from benchmarks.ai_verification.artifact_grader import grade_artifacts

        (tmp_path / "config.py").write_text("DEFAULT_NORMALIZE = True\n")
        report = grade_artifacts(
            diff_patch="",
            changed_files=["config.py"],
            sandbox=tmp_path,
            assertions={"must_contain_text": {"config.py": ["DEFAULT_NORMALIZE = True"]}},
        )
        assert report.passed

    def test_must_contain_text_fails(self, tmp_path: Path):
        from benchmarks.ai_verification.artifact_grader import grade_artifacts

        (tmp_path / "config.py").write_text("DEFAULT_NORMALIZE = False\n")
        report = grade_artifacts(
            diff_patch="",
            changed_files=["config.py"],
            sandbox=tmp_path,
            assertions={"must_contain_text": {"config.py": ["DEFAULT_NORMALIZE = True"]}},
        )
        assert not report.passed

    def test_extract_changed_files(self):
        from benchmarks.ai_verification.artifact_grader import extract_changed_files

        diff = "diff --git a/store.py b/store.py\nindex abc..def 100644\n--- a/store.py\n+++ b/store.py\n"
        assert extract_changed_files(diff) == ["store.py"]


# ---------------------------------------------------------------------------
# HFIX-2: Verdict composition — trajectory failure forces FAIL
# ---------------------------------------------------------------------------


class TestVerdictComposition:
    def test_deterministic_pass_but_trajectory_fail_forces_fail(self):
        from benchmarks.ai_verification.scenario_yaml import load_scenario_yaml
        from benchmarks.ai_verification.schema import Verdict
        from benchmarks.ai_verification.run_scenario import run

        yaml_text = textwrap.dedent("""\
            title: Trajectory fail test
            category: backend_feature
            difficulty: easy
            target_stack:
              language: python
            task_spec:
              prompt: "Do something"
            expected_outcomes:
              must_have:
                - "thread_started event present"
            grading:
              checks:
                - snapshot
              check_commands:
                snapshot: "true"
            trajectory_assertions:
              must_use_tools:
                - "search_text"
        """)
        spec = load_scenario_yaml(yaml_text)

        from unittest.mock import patch
        import tempfile

        raw_lines = [
            json.dumps({"type": "thread_started", "protocol_version": "0.2.0-harness"}),
            json.dumps({"type": "tool_call_completed", "protocol_version": "0.2.0-harness", "tool_name": "edit_file", "tool_family": "file_write", "status": "success", "tool_call_id": "call-1", "started_at": "2026-05-01T00:00:00Z", "finished_at": "2026-05-01T00:00:01Z"}),
        ]

        with tempfile.TemporaryDirectory() as tmp_qa:
            qa_base = Path(tmp_qa)
            with patch("benchmarks.ai_verification.run_scenario._run_autocode", return_value=(0, 1, 100, 50, [], "", raw_lines)):
                run_id, report = run(
                    scenario_path=_write_temp_scenario(spec),
                    agent="autocode",
                    qa_base=qa_base,
                )
            assert report.verdict == Verdict.FAIL

    def test_required_tool_assertion_with_no_typed_calls_forces_fail(self):
        from benchmarks.ai_verification.scenario_yaml import load_scenario_yaml
        from benchmarks.ai_verification.schema import Verdict
        from benchmarks.ai_verification.run_scenario import run

        yaml_text = textwrap.dedent("""\
            title: Missing required tool fails
            category: backend_feature
            difficulty: easy
            target_stack:
              language: python
            task_spec:
              prompt: "Ask the user for clarification"
            expected_outcomes:
              must_have: []
            grading:
              checks:
                - snapshot
              check_commands:
                snapshot: "true"
            trajectory_assertions:
              must_use_tools:
                - "ask_user"
        """)
        spec = load_scenario_yaml(yaml_text)

        from unittest.mock import patch
        import tempfile

        raw_lines = [
            json.dumps({"type": "thread_started", "protocol_version": "0.2.0-harness"}),
        ]

        with tempfile.TemporaryDirectory() as tmp_qa:
            qa_base = Path(tmp_qa)
            with patch(
                "benchmarks.ai_verification.run_scenario._run_autocode",
                return_value=(0, 0, 100, 50, [], "", raw_lines),
            ):
                run_id, report = run(
                    scenario_path=_write_temp_scenario(spec),
                    agent="autocode",
                    qa_base=qa_base,
                )
            assert report.verdict == Verdict.FAIL
            assert report.trajectory_passed is False
            trajectory = json.loads((qa_base / run_id / "trajectory_report.json").read_text())
            assert trajectory["passed"] is False
            summary = json.loads((qa_base / run_id / "run_summary.json").read_text())
            assert summary["required_tools_satisfied"] is False
            assert summary["trajectory_satisfied"] is False

    def test_min_turns_assertion_with_one_turn_forces_fail(self):
        from benchmarks.ai_verification.scenario_yaml import load_scenario_yaml
        from benchmarks.ai_verification.schema import Verdict
        from benchmarks.ai_verification.run_scenario import run

        yaml_text = textwrap.dedent("""\
            title: Missing second turn fails
            category: long_horizon
            difficulty: medium
            target_stack:
              language: python
            task_spec:
              prompt: "Fix this over multiple turns"
            expected_outcomes:
              must_have: []
            grading:
              checks:
                - snapshot
              check_commands:
                snapshot: "true"
            turn_assertions:
              min_turns: 2
        """)
        spec = load_scenario_yaml(yaml_text)

        from unittest.mock import patch
        import tempfile

        raw_lines = [
            json.dumps({"type": "thread_started", "protocol_version": "0.2.0-harness"}),
        ]
        turns = [{"turn": 1, "grading_passed": True, "event_count": 1}]

        with tempfile.TemporaryDirectory() as tmp_qa:
            qa_base = Path(tmp_qa)
            with patch(
                "benchmarks.ai_verification.run_scenario._run_autocode",
                return_value=(0, 0, 100, 50, [], "", raw_lines, 1, turns),
            ):
                run_id, report = run(
                    scenario_path=_write_temp_scenario(spec),
                    agent="autocode",
                    qa_base=qa_base,
                )
            assert report.verdict == Verdict.FAIL
            summary = json.loads((qa_base / run_id / "run_summary.json").read_text())
            assert summary["turn_count"] == 1
            assert summary["turn_assertions_satisfied"] is False
            turns_json = json.loads((qa_base / run_id / "turns.json").read_text())
            assert turns_json == turns

    def test_provider_429_is_infra_fail_in_run_report(self):
        from benchmarks.ai_verification.scenario_yaml import load_scenario_yaml
        from benchmarks.ai_verification.schema import Verdict
        from benchmarks.ai_verification.run_scenario import run

        yaml_text = textwrap.dedent("""\
            title: Provider failure test
            category: backend_feature
            difficulty: easy
            target_stack:
              language: python
            task_spec:
              prompt: "Do something"
            expected_outcomes:
              must_have: []
            grading:
              checks:
                - snapshot
              check_commands:
                snapshot: "true"
        """)
        spec = load_scenario_yaml(yaml_text)

        from unittest.mock import patch
        import tempfile

        raw_lines = [
            json.dumps({
                "type": "error",
                "protocol_version": "0.2.0-harness",
                "message": "HTTP 429 Too Many Requests",
            }),
        ]

        with tempfile.TemporaryDirectory() as tmp_qa:
            qa_base = Path(tmp_qa)
            with patch(
                "benchmarks.ai_verification.run_scenario._run_autocode",
                return_value=(1, 0, 0, 0, [], "HTTP 429 Too Many Requests", raw_lines, 1, []),
            ):
                run_id, report = run(
                    scenario_path=_write_temp_scenario(spec),
                    agent="autocode",
                    qa_base=qa_base,
                )
            assert report.verdict == Verdict.INFRA_FAIL
            meta = json.loads((qa_base / run_id / "meta.json").read_text())
            assert meta["infra_fail_reason"]
            summary = json.loads((qa_base / run_id / "run_summary.json").read_text())
            assert summary["infra_fail_reason"] == meta["infra_fail_reason"]
            assert summary["verdict"] == "INFRA_FAIL"
            assert summary["primary_verdict"] == "PASS"
            assert "infra_signals" in summary
            assert "rate_limit_detected" in summary["infra_signals"]
            assert "agent_fail_signals" in summary
            assert "agent_exit_nonzero" in summary["agent_fail_signals"]

    def test_infra_blocked_run_still_reports_underlying_agent_failures(self):
        from benchmarks.ai_verification.scenario_yaml import load_scenario_yaml
        from benchmarks.ai_verification.schema import Verdict
        from benchmarks.ai_verification.run_scenario import run

        yaml_text = textwrap.dedent("""\
            title: Mixed infra and agent failure test
            category: backend_feature
            difficulty: easy
            target_stack:
              language: python
            task_spec:
              prompt: "Do something"
            expected_outcomes:
              must_have: []
            grading:
              checks:
                - snapshot
              check_commands:
                snapshot: "false"
        """)
        spec = load_scenario_yaml(yaml_text)

        from unittest.mock import patch
        import tempfile

        raw_lines = [
            json.dumps({
                "type": "error",
                "protocol_version": "0.2.0-harness",
                "message": "HTTP 429 Too Many Requests",
            }),
        ]

        with tempfile.TemporaryDirectory() as tmp_qa:
            qa_base = Path(tmp_qa)
            with patch(
                "benchmarks.ai_verification.run_scenario._run_autocode",
                return_value=(1, 0, 0, 0, [], "HTTP 429 Too Many Requests", raw_lines, 1, []),
            ):
                run_id, report = run(
                    scenario_path=_write_temp_scenario(spec),
                    agent="autocode",
                    qa_base=qa_base,
                )

            assert report.verdict == Verdict.INFRA_FAIL
            summary = json.loads((qa_base / run_id / "run_summary.json").read_text())
            assert summary["verdict"] == "INFRA_FAIL"
            assert summary["primary_verdict"] == "FAIL"
            assert summary["infra_blocks_verdict"] is True
            assert "rate_limit_detected" in summary["infra_signals"]
            assert "agent_exit_nonzero" in summary["agent_fail_signals"]
            assert "deterministic_checks_failed" in summary["agent_fail_signals"]

    def test_recovered_provider_warning_does_not_override_passing_run(self):
        from benchmarks.ai_verification.scenario_yaml import load_scenario_yaml
        from benchmarks.ai_verification.schema import Verdict
        from benchmarks.ai_verification.run_scenario import run

        yaml_text = textwrap.dedent("""\
            title: Recovered provider warning test
            category: backend_feature
            difficulty: easy
            target_stack:
              language: python
            task_spec:
              prompt: "Do something"
            expected_outcomes:
              must_have:
                - "turn_completed event with usage"
            grading:
              checks:
                - snapshot
              check_commands:
                snapshot: "true"
        """)
        spec = load_scenario_yaml(yaml_text)

        from unittest.mock import patch
        import tempfile

        raw_lines = [
            json.dumps({
                "type": "error",
                "protocol_version": "0.2.0-harness",
                "message": "HTTP 429 Too Many Requests; retry recovered",
            }),
            json.dumps({
                "type": "turn_completed",
                "protocol_version": "0.2.0-harness",
                "usage": {"input_tokens": 100, "output_tokens": 50},
            }),
        ]

        with tempfile.TemporaryDirectory() as tmp_qa:
            qa_base = Path(tmp_qa)
            with patch(
                "benchmarks.ai_verification.run_scenario._run_autocode",
                return_value=(0, 1, 100, 50, [], "", raw_lines, 1, [{"turn": 1, "grading_passed": True}]),
            ):
                run_id, report = run(
                    scenario_path=_write_temp_scenario(spec),
                    agent="autocode",
                    qa_base=qa_base,
                )
            assert report.verdict == Verdict.PASS
            meta = json.loads((qa_base / run_id / "meta.json").read_text())
            assert meta["infra_fail_reason"] == ""
            summary = json.loads((qa_base / run_id / "run_summary.json").read_text())
            assert summary["infra_fail_reason"] == ""
            assert summary["infra_detected"] is True
            assert summary["infra_blocks_verdict"] is False
            assert "rate_limit_detected" in summary["infra_signals"]

    def test_deterministic_pass_but_artifact_assertion_fail_forces_fail(self):
        from benchmarks.ai_verification.scenario_yaml import load_scenario_yaml
        from benchmarks.ai_verification.schema import Verdict
        from benchmarks.ai_verification.run_scenario import run

        yaml_text = textwrap.dedent("""\
            title: Noop refactor guard test
            category: refactor
            difficulty: easy
            target_stack:
              language: python
            task_spec:
              prompt: "Refactor this code"
            expected_outcomes:
              must_have:
                - "thread_started event present"
            grading:
              checks:
                - snapshot
              check_commands:
                snapshot: "true"
            artifact_assertions:
              forbid_noop_pass: true
              require_non_empty_diff: true
        """)
        spec = load_scenario_yaml(yaml_text)

        from unittest.mock import patch
        import tempfile

        raw_lines = [
            json.dumps({"type": "thread_started", "protocol_version": "0.2.0-harness"}),
        ]

        with tempfile.TemporaryDirectory() as tmp_qa:
            qa_base = Path(tmp_qa)
            with patch("benchmarks.ai_verification.run_scenario._run_autocode", return_value=(0, 0, 100, 50, [], "", raw_lines)):
                run_id, report = run(
                    scenario_path=_write_temp_scenario(spec),
                    agent="autocode",
                    qa_base=qa_base,
                )
            assert report.verdict == Verdict.FAIL


# ---------------------------------------------------------------------------
# HFIX-3: Run artifacts
# ---------------------------------------------------------------------------


class TestRunArtifacts:
    def test_tool_calls_jsonl_written_on_pass(self):
        from benchmarks.ai_verification.scenario_yaml import load_scenario_yaml
        from benchmarks.ai_verification.run_scenario import run

        yaml_text = textwrap.dedent("""\
            title: Artifact test
            category: backend_feature
            difficulty: easy
            target_stack:
              language: python
            task_spec:
              prompt: "Do something"
            expected_outcomes:
              must_have:
                - "thread_started event present"
            grading:
              checks:
                - snapshot
              check_commands:
                snapshot: "true"
        """)
        spec = load_scenario_yaml(yaml_text)

        from unittest.mock import patch
        import tempfile

        raw_lines = [
            json.dumps({"type": "thread_started", "protocol_version": "0.2.0-harness"}),
            json.dumps({"type": "tool_call_completed", "protocol_version": "0.2.0-harness", "tool_name": "edit_file", "tool_family": "file_write", "status": "success", "tool_call_id": "call-1", "started_at": "2026-05-01T00:00:00Z", "finished_at": "2026-05-01T00:00:01Z"}),
        ]

        with tempfile.TemporaryDirectory() as tmp_qa:
            qa_base = Path(tmp_qa)
            with patch("benchmarks.ai_verification.run_scenario._run_autocode", return_value=(0, 1, 100, 50, [], "", raw_lines)):
                run_id, report = run(
                    scenario_path=_write_temp_scenario(spec),
                    agent="autocode",
                    qa_base=qa_base,
                )
            tc_path = qa_base / run_id / "tool_calls.jsonl"
            assert tc_path.exists()
            lines = tc_path.read_text().strip().splitlines()
            assert len(lines) == 1
            assert json.loads(lines[0])["tool_name"] == "edit_file"

    def test_run_summary_written(self):
        from benchmarks.ai_verification.scenario_yaml import load_scenario_yaml
        from benchmarks.ai_verification.run_scenario import run

        yaml_text = textwrap.dedent("""\
            title: Summary test
            category: backend_feature
            difficulty: easy
            target_stack:
              language: python
            task_spec:
              prompt: "Do something"
            expected_outcomes:
              must_have:
                - "thread_started event present"
            grading:
              checks:
                - snapshot
              check_commands:
                snapshot: "true"
        """)
        spec = load_scenario_yaml(yaml_text)

        from unittest.mock import patch
        import tempfile

        raw_lines = [
            json.dumps({"type": "thread_started", "protocol_version": "0.2.0-harness"}),
        ]

        with tempfile.TemporaryDirectory() as tmp_qa:
            qa_base = Path(tmp_qa)
            with patch("benchmarks.ai_verification.run_scenario._run_autocode", return_value=(0, 0, 100, 50, [], "", raw_lines)):
                run_id, report = run(
                    scenario_path=_write_temp_scenario(spec),
                    agent="autocode",
                    qa_base=qa_base,
                )
            summary_path = qa_base / run_id / "run_summary.json"
            assert summary_path.exists()
            summary = json.loads(summary_path.read_text())
            assert summary["verdict"] == "PASS"
            assert "tool_histogram" in summary
            assert "changed_files" in summary

    def test_artifact_report_written_and_embedded_in_grading_report(self):
        from benchmarks.ai_verification.scenario_yaml import load_scenario_yaml
        from benchmarks.ai_verification.run_scenario import run
        from benchmarks.ai_verification.schema import Verdict

        yaml_text = textwrap.dedent("""\
            title: Artifact report persistence
            category: backend_feature
            difficulty: easy
            target_stack:
              language: python
            task_spec:
              prompt: "Do something"
            expected_outcomes:
              must_have:
                - "thread_started event present"
            grading:
              checks:
                - snapshot
              check_commands:
                snapshot: "true"
            artifact_assertions:
              require_non_empty_diff: true
              must_change_files:
                - "processor.py"
        """)
        spec = load_scenario_yaml(yaml_text)

        from unittest.mock import patch
        import tempfile

        raw_lines = [
            json.dumps({"type": "thread_started", "protocol_version": "0.2.0-harness"}),
        ]

        with tempfile.TemporaryDirectory() as tmp_qa:
            qa_base = Path(tmp_qa)
            with patch(
                "benchmarks.ai_verification.run_scenario._run_autocode",
                return_value=(0, 0, 100, 50, [], "", raw_lines),
            ):
                run_id, report = run(
                    scenario_path=_write_temp_scenario(spec),
                    agent="autocode",
                    qa_base=qa_base,
                )
            assert report.verdict == Verdict.FAIL
            artifact = json.loads((qa_base / run_id / "artifact_report.json").read_text())
            grading = json.loads((qa_base / run_id / "grading_report.json").read_text())
            assert artifact["passed"] is False
            assert artifact["results"]
            assert grading["artifact_results"] == artifact["results"]

    def test_hidden_immutable_tests_fail_when_agent_rewrites_visible_tests(self):
        from benchmarks.ai_verification.scenario_yaml import load_scenario_yaml
        from benchmarks.ai_verification.run_scenario import run
        from benchmarks.ai_verification.schema import Verdict

        yaml_text = textwrap.dedent("""\
            title: Hidden immutable test catches API rewrite
            category: backend_feature
            difficulty: easy
            target_stack:
              language: python
            task_spec:
              prompt: "Implement KVStore without renaming it."
            repo_seed:
              mode: fresh
              files:
                store.py: |
                  class KVStore:
                      pass
                test_store.py: |
                  def test_visible_rewritten_by_agent():
                      assert True
            expected_outcomes:
              must_have:
                - "thread_started event present"
            grading:
              checks:
                - run_tests
              check_commands:
                run_tests: "python -m pytest test_store.py -q"
            artifact_assertions:
              hidden_test_files:
                test_hidden_api.py: |
                  from store import KVStore

                  def test_kvstore_public_api_preserved():
                      store = KVStore()
                      store.set("k", "v")
                      assert store.get("k") == "v"
              hidden_test_command: "python -m pytest .autocode_hidden_tests -q"
        """)
        spec = load_scenario_yaml(yaml_text)

        from unittest.mock import patch
        import tempfile

        raw_lines = [
            json.dumps({"type": "thread_started", "protocol_version": "0.2.0-harness"}),
        ]

        def fake_agent(*_args, **_kwargs):
            sandbox = _kwargs.get("sandbox")
            if sandbox is None and len(_args) >= 2:
                sandbox = _args[1]
            Path(sandbox, "store.py").write_text(
                "class KeyValueStore:\n"
                "    def set(self, key, value): pass\n"
                "    def get(self, key): return value\n",
                encoding="utf-8",
            )
            Path(sandbox, "test_store.py").write_text(
                "def test_visible_passes_after_rewrite():\n    assert True\n",
                encoding="utf-8",
            )
            return (0, 0, 100, 50, [], "", raw_lines, 1, [{"turn": 1, "grading_passed": False}])

        with tempfile.TemporaryDirectory() as tmp_qa:
            qa_base = Path(tmp_qa)
            with patch("benchmarks.ai_verification.run_scenario._run_autocode", side_effect=fake_agent):
                run_id, report = run(
                    scenario_path=_write_temp_scenario(spec),
                    agent="autocode",
                    qa_base=qa_base,
                )
            assert report.verdict == Verdict.FAIL
            test_log = (qa_base / run_id / "test_log.txt").read_text()
            assert "hidden-tests" in test_log
            assert "cannot import name 'KVStore'" in test_log

    def test_zero_pytest_collection_is_classified_in_check_output(self, tmp_path: Path):
        from benchmarks.ai_verification.run_scenario import _run_checks
        from benchmarks.ai_verification.scenario_yaml import load_scenario_yaml

        yaml_text = textwrap.dedent("""\
            title: Zero tests collection
            category: backend_feature
            difficulty: easy
            target_stack:
              language: python
            task_spec:
              prompt: "Do something"
            grading:
              checks:
                - run_tests
              check_commands:
                run_tests: "printf 'collected 0 items\\n'; exit 0"
        """)
        spec = load_scenario_yaml(yaml_text)

        results, test_log = _run_checks(spec, tmp_path)

        assert results[0].passed is False
        assert "HARNESS_CLASSIFICATION: zero_tests_collected" in results[0].output
        assert "HARNESS_CLASSIFICATION: zero_tests_collected" in test_log

    def test_missing_default_grading_command_does_not_pass(self, tmp_path: Path):
        from benchmarks.ai_verification.run_scenario import _run_checks
        from benchmarks.ai_verification.scenario_yaml import load_scenario_yaml

        yaml_text = textwrap.dedent("""\
            title: Missing default grading command
            category: backend_feature
            difficulty: easy
            target_stack:
              language: unknownlang
            task_spec:
              prompt: "Do something"
            grading:
              checks:
                - run_tests
        """)
        spec = load_scenario_yaml(yaml_text)

        results, test_log = _run_checks(spec, tmp_path)

        assert results[0].passed is False
        assert "HARNESS_CLASSIFICATION: missing_grading_command" in results[0].output
        assert "HARNESS_CLASSIFICATION: missing_grading_command" in test_log

    def test_cached_empty_test_log_does_not_regrade_as_pass(self, tmp_path: Path):
        from benchmarks.ai_verification.grade_run import grade
        from benchmarks.ai_verification.scenario_yaml import load_scenario_yaml
        from benchmarks.ai_verification.schema import Verdict

        spec = load_scenario_yaml(textwrap.dedent("""\
            title: Empty cached grading output
            category: backend_feature
            difficulty: easy
            target_stack:
              language: python
            task_spec:
              prompt: "Do something"
            grading:
              checks:
                - run_tests
              check_commands:
                run_tests: "python -m pytest test_empty.py -q"
        """))
        run_dir = tmp_path / "empty-log-run"
        run_dir.mkdir()
        spec.save(run_dir / "scenario.json")
        (run_dir / "test_log.txt").write_text("")

        report = grade("empty-log-run", base=tmp_path, ai_review=False)

        assert report.verdict == Verdict.FAIL
        assert report.check_results[0].passed is False
        assert "HARNESS_CLASSIFICATION: empty_grading_output" in report.check_results[0].output

    def test_cached_zero_test_log_does_not_regrade_as_pass(self, tmp_path: Path):
        from benchmarks.ai_verification.grade_run import grade
        from benchmarks.ai_verification.scenario_yaml import load_scenario_yaml
        from benchmarks.ai_verification.schema import Verdict

        spec = load_scenario_yaml(textwrap.dedent("""\
            title: Cached zero-test output
            category: backend_feature
            difficulty: easy
            target_stack:
              language: python
            task_spec:
              prompt: "Do something"
            grading:
              checks:
                - run_tests
              check_commands:
                run_tests: "python -m pytest test_empty.py -q"
        """))
        run_dir = tmp_path / "zero-tests-run"
        run_dir.mkdir()
        spec.save(run_dir / "scenario.json")
        (run_dir / "test_log.txt").write_text("collected 0 items\n")

        report = grade("zero-tests-run", base=tmp_path, ai_review=False)

        assert report.verdict == Verdict.FAIL
        assert report.check_results[0].passed is False
        assert "HARNESS_CLASSIFICATION: zero_tests_collected" in report.check_results[0].output

    def test_turns_json_written_with_real_turn_count(self):
        from benchmarks.ai_verification.scenario_yaml import load_scenario_yaml
        from benchmarks.ai_verification.run_scenario import run

        yaml_text = textwrap.dedent("""\
            title: Turns artifact test
            category: backend_feature
            difficulty: easy
            target_stack:
              language: python
            task_spec:
              prompt: "Do something"
            expected_outcomes:
              must_have: []
            grading:
              checks:
                - snapshot
              check_commands:
                snapshot: "true"
        """)
        spec = load_scenario_yaml(yaml_text)

        from unittest.mock import patch
        import tempfile

        turns = [
            {"turn": 1, "grading_passed": False, "event_count": 3},
            {"turn": 2, "grading_passed": True, "event_count": 5},
        ]
        raw_lines = [
            json.dumps({"type": "thread_started", "protocol_version": "0.2.0-harness"}),
        ]

        with tempfile.TemporaryDirectory() as tmp_qa:
            qa_base = Path(tmp_qa)
            with patch(
                "benchmarks.ai_verification.run_scenario._run_autocode",
                return_value=(0, 0, 100, 50, [], "", raw_lines, 2, turns),
            ):
                run_id, report = run(
                    scenario_path=_write_temp_scenario(spec),
                    agent="autocode",
                    qa_base=qa_base,
                )
            turns_path = qa_base / run_id / "turns.json"
            assert turns_path.exists()
            assert json.loads(turns_path.read_text()) == turns
            summary = json.loads((qa_base / run_id / "run_summary.json").read_text())
            assert summary["turn_count"] == 2


# ---------------------------------------------------------------------------
# HFIX-2: YAML assertion loading
# ---------------------------------------------------------------------------


class TestYamlAssertionLoading:
    def test_loads_trajectory_assertions(self):
        from benchmarks.ai_verification.scenario_yaml import load_scenario_yaml

        yaml_text = textwrap.dedent("""\
            title: Trajectory test
            category: backend_feature
            difficulty: easy
            target_stack:
              language: python
            task_spec:
              prompt: "Search then edit"
            trajectory_assertions:
              must_use_tools:
                - "search_text"
                - "edit_file"
              in_order_tools:
                - "search_text"
                - "edit_file"
              min_tool_calls: 2
        """)
        spec = load_scenario_yaml(yaml_text)
        assert spec.trajectory_assertions["must_use_tools"] == ["search_text", "edit_file"]
        assert spec.trajectory_assertions["in_order_tools"] == ["search_text", "edit_file"]
        assert spec.trajectory_assertions["min_tool_calls"] == 2

    def test_loads_artifact_assertions(self):
        from benchmarks.ai_verification.scenario_yaml import load_scenario_yaml

        yaml_text = textwrap.dedent("""\
            title: Artifact assertion test
            category: refactor
            difficulty: medium
            target_stack:
              language: python
            task_spec:
              prompt: "Refactor"
            artifact_assertions:
              require_non_empty_diff: true
              forbid_noop_pass: true
              must_change_files:
                - "config.py"
              must_not_change_files:
                - "test_config.py"
        """)
        spec = load_scenario_yaml(yaml_text)
        assert spec.artifact_assertions["require_non_empty_diff"] is True
        assert spec.artifact_assertions["forbid_noop_pass"] is True
        assert spec.artifact_assertions["must_change_files"] == ["config.py"]

    def test_loads_turn_assertions(self):
        from benchmarks.ai_verification.scenario_yaml import load_scenario_yaml

        yaml_text = textwrap.dedent("""\
            title: Turn assertion test
            category: long_horizon
            difficulty: hard
            target_stack:
              language: python
            task_spec:
              prompt: "Build pipeline"
            turn_assertions:
              min_turns: 3
              max_turns: 5
              no_regression_after_pass: true
        """)
        spec = load_scenario_yaml(yaml_text)
        assert spec.turn_assertions["min_turns"] == 3
        assert spec.turn_assertions["no_regression_after_pass"] is True


class TestScenarioLint:
    def test_flags_seeded_visible_tests_without_hidden_or_forbidden_policy(self):
        from benchmarks.ai_verification.scenario_lint import lint_seeded_test_protection
        from benchmarks.ai_verification.scenario_yaml import load_scenario_yaml

        spec = load_scenario_yaml(textwrap.dedent("""\
            title: Unprotected seeded test
            category: backend_feature
            difficulty: easy
            target_stack:
              language: python
            task_spec:
              prompt: "Implement processor.py"
            repo_seed:
              mode: fresh
              files:
                test_processor.py: |
                  from processor import process_numbers

                  def test_process_numbers():
                      assert process_numbers([2]) == [4]
        """))

        findings = lint_seeded_test_protection(spec)

        assert len(findings) == 1
        assert findings[0].code == "seeded_test_unprotected"
        assert findings[0].path == "test_processor.py"

    def test_allows_seeded_visible_test_protected_by_must_not_change_files(self):
        from benchmarks.ai_verification.scenario_lint import lint_seeded_test_protection
        from benchmarks.ai_verification.scenario_yaml import load_scenario_yaml

        spec = load_scenario_yaml(textwrap.dedent("""\
            title: Protected seeded test
            category: backend_feature
            difficulty: easy
            target_stack:
              language: python
            task_spec:
              prompt: "Implement processor.py"
            repo_seed:
              mode: fresh
              files:
                tests/test_processor.py: |
                  from processor import process_numbers

                  def test_process_numbers():
                      assert process_numbers([2]) == [4]
            artifact_assertions:
              must_not_change_files:
                - tests/test_processor.py
        """))

        assert lint_seeded_test_protection(spec) == []

    def test_allows_seeded_visible_test_protected_by_hidden_tests(self):
        from benchmarks.ai_verification.scenario_lint import lint_seeded_test_protection
        from benchmarks.ai_verification.scenario_yaml import load_scenario_yaml

        spec = load_scenario_yaml(textwrap.dedent("""\
            title: Hidden-test protected seeded test
            category: backend_feature
            difficulty: easy
            target_stack:
              language: python
            task_spec:
              prompt: "Implement processor.py"
            repo_seed:
              mode: fresh
              files:
                test_processor.py: |
                  from processor import process_numbers

                  def test_process_numbers():
                      assert process_numbers([2]) == [4]
            artifact_assertions:
              hidden_test_files:
                test_hidden_processor.py: |
                  from processor import process_numbers

                  def test_hidden_process_numbers():
                      assert process_numbers([3]) == [27]
        """))

        assert lint_seeded_test_protection(spec) == []


def _write_temp_scenario(spec) -> Path:
    import tempfile
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    spec.save(Path(f.name))
    f.close()
    return Path(f.name)


# ---------------------------------------------------------------------------
# HFIX-4: Infrastructure classification
# ---------------------------------------------------------------------------


class TestInfraClassification:
    def test_empty_turn_classified_as_infra_fail(self):
        from benchmarks.ai_verification.infra_classifier import classify_infra

        result = classify_infra(events=[], error="", turn_count=0)
        assert result.is_infra_fail
        assert "empty_turn" in result.signals

    def test_rate_limit_429_classified_as_infra_fail(self):
        from benchmarks.ai_verification.infra_classifier import classify_infra

        result = classify_infra(
            events=[],
            error="HTTP 429 Too Many Requests from provider",
            turn_count=1,
        )
        assert result.is_infra_fail
        assert "rate_limit_detected" in result.signals

    def test_rate_limit_from_error_event(self):
        from benchmarks.ai_verification.infra_classifier import classify_infra

        result = classify_infra(
            events=[{"type": "error", "message": "rate limit exceeded"}],
            error="",
            turn_count=1,
        )
        assert result.is_infra_fail
        assert "rate_limit_detected" in result.signals

    def test_gateway_unreachable_message_is_infra_fail(self):
        from benchmarks.ai_verification.infra_classifier import classify_infra

        result = classify_infra(
            events=[],
            error="Could not reach the configured gateway at http://localhost:4000/v1",
            turn_count=1,
        )

        assert result.is_infra_fail
        assert "rate_limit_detected" in result.signals

    def test_sandbox_failure_classified_as_infra_fail(self):
        from benchmarks.ai_verification.infra_classifier import classify_infra

        result = classify_infra(
            events=[],
            error="sandbox setup failed: No such file or directory",
            turn_count=1,
        )
        assert result.is_infra_fail
        assert "sandbox_failure" in result.signals

    def test_grading_command_failure_classified_as_infra_fail(self):
        from benchmarks.ai_verification.infra_classifier import classify_infra

        result = classify_infra(
            events=[],
            error="",
            turn_count=1,
            check_output="can't open file 'grading_runner.py': No such file or directory\n=== test_run ===\n1 PASSED",
        )
        assert result.is_infra_fail
        assert "grading_command_failure" in result.signals

    def test_agent_induced_test_failure_not_infra_fail(self):
        from benchmarks.ai_verification.infra_classifier import classify_infra

        result = classify_infra(
            events=[],
            error="",
            turn_count=1,
            check_output="=== test_run ===\nNo module named 'deleted_module'\n2 FAILED, 3 PASSED",
        )
        assert not result.is_infra_fail

    def test_missing_dependency_module_not_found_is_infra_fail(self):
        from benchmarks.ai_verification.infra_classifier import classify_infra

        result = classify_infra(
            events=[],
            error="",
            turn_count=1,
            check_output=(
                "ImportError while importing test module 'tests/test_discord_clone_product.py'.\n"
                "ModuleNotFoundError: No module named 'selenium'\n"
            ),
        )

        assert result.is_infra_fail
        assert "missing_dependency" in result.signals

    def test_missing_dependency_plain_import_error_is_infra_fail(self):
        from benchmarks.ai_verification.infra_classifier import classify_infra

        result = classify_infra(
            events=[],
            error="",
            turn_count=1,
            check_output="ImportError: No module named playwright\n",
        )

        assert result.is_infra_fail
        assert "missing_dependency" in result.signals

    def test_timeout_classified_as_infra_fail(self):
        from benchmarks.ai_verification.infra_classifier import classify_infra

        result = classify_infra(
            events=[],
            error="agent timed out after 120s",
            turn_count=1,
        )
        assert result.is_infra_fail
        assert "timeout" in result.signals

    def test_real_assertion_failure_not_infra_fail(self):
        from benchmarks.ai_verification.infra_classifier import classify_infra

        events = [
            {"type": "thread_started", "protocol_version": "0.2.0-harness"},
            {"type": "item_started", "kind": "tool_execution"},
            {"type": "item_completed"},
            {"type": "tool_call_completed", "tool_name": "edit_file", "tool_family": "file_write", "status": "success"},
            {"type": "turn_completed", "usage": {"input_tokens": 100, "output_tokens": 50}},
        ]
        result = classify_infra(
            events=events,
            error="",
            turn_count=1,
            check_output="2 FAILED, 3 PASSED",
        )
        assert not result.is_infra_fail

    def test_productive_turn_not_infra_fail(self):
        from benchmarks.ai_verification.infra_classifier import classify_infra

        events = [
            {"type": "tool_call_completed", "tool_name": "edit_file", "tool_family": "file_write", "status": "success"},
        ]
        result = classify_infra(events=events, error="", turn_count=1)
        assert not result.is_infra_fail


# ---------------------------------------------------------------------------
# HFIX-5: Canary loading and validation
# ---------------------------------------------------------------------------


class TestCanaryLoading:
    def _scenario_path(self, name: str) -> Path:
        return PROJECT_ROOT / "benchmarks" / "ai_verification" / "scenarios" / name

    def test_semantic_search_required_loads(self):
        from benchmarks.ai_verification.scenario_yaml import load_scenario_yaml_file
        spec = load_scenario_yaml_file(self._scenario_path("semantic-search-required.yaml"))
        assert spec.title == "Semantic search required"
        assert spec.trajectory_assertions["must_use_tools"] == ["semantic_search"]
        assert spec.artifact_assertions["forbid_noop_pass"] is True

    def test_spawn_subagent_required_loads(self):
        from benchmarks.ai_verification.scenario_yaml import load_scenario_yaml_file
        spec = load_scenario_yaml_file(self._scenario_path("spawn-subagent-required.yaml"))
        assert "spawn_subagent" in spec.trajectory_assertions["must_use_tools"]
        assert "check_subagent" in spec.trajectory_assertions["must_use_tools"]

    def test_ask_user_scripted_loads(self):
        from benchmarks.ai_verification.scenario_yaml import load_scenario_yaml_file
        spec = load_scenario_yaml_file(self._scenario_path("ask-user-scripted.yaml"))
        assert "ask_user" in spec.trajectory_assertions["must_use_tools"]
        assert "test_processor.py" in spec.artifact_assertions["must_not_change_files"]

    def test_refactor_noop_guard_loads(self):
        from benchmarks.ai_verification.scenario_yaml import load_scenario_yaml_file
        spec = load_scenario_yaml_file(self._scenario_path("refactor-noop-guard.yaml"))
        assert spec.artifact_assertions["forbid_noop_pass"] is True
        assert spec.artifact_assertions["require_non_empty_diff"] is True
        assert "calculator.py" in spec.artifact_assertions["must_change_files"]

    def test_multi_turn_regression_loads(self):
        from benchmarks.ai_verification.scenario_yaml import load_scenario_yaml_file
        spec = load_scenario_yaml_file(self._scenario_path("multi-turn-regression.yaml"))
        assert spec.turn_assertions["min_turns"] == 2
        assert spec.turn_assertions["no_regression_after_pass"] is True
        assert "test_store.py" in spec.artifact_assertions["must_not_change_files"]
        assert "test_get_set" in spec.artifact_assertions["must_contain_text"]["test_store.py"]
        assert "test_delete" in spec.artifact_assertions["must_contain_text"]["test_store.py"]
        assert "test_hidden_kvstore_api.py" in spec.artifact_assertions["hidden_test_files"]

    def test_tool_trajectory_git_loads(self):
        from benchmarks.ai_verification.scenario_yaml import load_scenario_yaml_file
        spec = load_scenario_yaml_file(self._scenario_path("tool-trajectory-git.yaml"))
        assert spec.trajectory_assertions["in_order_tools"] == ["git_status", "git_diff"]
        assert "edit_file" in spec.trajectory_assertions["must_use_tools"]
        assert "math_utils.py" in spec.artifact_assertions["must_change_files"]
        assert "test_math_utils.py" in spec.artifact_assertions["must_not_change_files"]

    def test_hfix_acceptance_script_runs_all_pinned_scenarios(self):
        # The acceptance script is a harness-tester artifact; after the split
        # into autocode-full it lives under harness-tester/ (and the frozen
        # lowrescoder/ archive), not at the workspace root. Probe both.
        rel = Path("scripts") / "02-run-hfix-live-acceptance.sh"
        candidates = [
            PROJECT_ROOT / "benchmarks" / rel,
            PROJECT_ROOT / rel,
            PROJECT_ROOT / "lowrescoder" / rel,
        ]
        script = next((c for c in candidates if c.exists()), candidates[0])
        text = script.read_text(encoding="utf-8")

        for scenario in [
            "multi-turn-regression.yaml",
            "ask-user-scripted.yaml",
            "semantic-search-required.yaml",
            "spawn-subagent-required.yaml",
            "tool-trajectory-git.yaml",
            "refactor-noop-guard.yaml",
        ]:
            assert scenario in text

        assert "set -e" not in text
        assert "failures=$((failures + 1))" in text

    def test_all_hfix_yaml_scenarios_protect_seeded_visible_tests(self):
        from benchmarks.ai_verification.scenario_lint import lint_seeded_test_protection
        from benchmarks.ai_verification.scenario_yaml import load_scenario_yaml_file

        scenario_dir = PROJECT_ROOT / "benchmarks" / "ai_verification" / "scenarios"
        findings_by_file = {}
        for path in sorted(scenario_dir.glob("*.yaml")):
            findings = lint_seeded_test_protection(load_scenario_yaml_file(path))
            if findings:
                findings_by_file[path.name] = [f"{finding.code}:{finding.path}" for finding in findings]

        assert findings_by_file == {}

    def test_early_substrate_scenarios_have_explicit_snapshot_commands(self):
        from benchmarks.ai_verification.scenario_yaml import load_scenario_yaml_file

        scenario_dir = PROJECT_ROOT / "benchmarks" / "ai_verification" / "scenarios"
        for name in [
            "01-simple-edit.yaml",
            "02-tool-output-shape.yaml",
            "03-session-persistence.yaml",
            "04-cost-routing.yaml",
            "05-headless-ndjson.yaml",
            "06-cache-hit-ratio.yaml",
        ]:
            spec = load_scenario_yaml_file(scenario_dir / name)
            assert spec.grading.check_commands.get("snapshot"), name

    def test_behavioral_substrate_scenarios_have_artifact_contracts(self):
        from benchmarks.ai_verification.scenario_yaml import load_scenario_yaml_file

        scenario_dir = PROJECT_ROOT / "benchmarks" / "ai_verification" / "scenarios"
        simple_edit = load_scenario_yaml_file(scenario_dir / "01-simple-edit.yaml")
        session_probe = load_scenario_yaml_file(scenario_dir / "03-session-persistence.yaml")
        cache_probe = load_scenario_yaml_file(scenario_dir / "06-cache-hit-ratio.yaml")

        assert "hello.py" in simple_edit.artifact_assertions["must_change_files"]
        assert "state.txt" in session_probe.artifact_assertions["must_change_files"]
        assert simple_edit.trajectory_assertions["must_use_tool_families"] == ["file_write", "file_read"]
        assert session_probe.trajectory_assertions["must_use_tool_families"] == ["file_write", "file_read"]
        assert cache_probe.turn_assertions["min_turns"] == 2


# ---------------------------------------------------------------------------
# HFIX-6: Summarize runs
# ---------------------------------------------------------------------------


class TestSummarizeRuns:
    def test_handles_old_runs_without_new_artifacts(self, tmp_path: Path):
        from benchmarks.ai_verification.summarize_runs import scan_run

        run_dir = tmp_path / "20260501-oldrun"
        run_dir.mkdir()
        (run_dir / "meta.json").write_text(json.dumps({
            "run_id": "20260501-oldrun",
            "status": "PASS",
            "wall_time_s": 45.2,
        }))
        (run_dir / "grading_report.json").write_text(json.dumps({"verdict": "PASS", "check_results": []}))

        summary = scan_run(run_dir)
        assert summary.verdict == "PASS"
        assert set(summary.missing_artifacts) == {
            "tool_calls.jsonl",
            "turns.json",
            "trajectory_report.json",
            "turn_report.json",
            "artifact_report.json",
            "run_summary.json",
        }

    def test_handles_new_format_runs(self, tmp_path: Path):
        from benchmarks.ai_verification.summarize_runs import scan_run

        run_dir = tmp_path / "20260502-newrun"
        run_dir.mkdir()
        (run_dir / "meta.json").write_text(json.dumps({
            "run_id": "20260502-newrun",
            "status": "FAIL",
            "wall_time_s": 91.5,
        }))
        (run_dir / "run_summary.json").write_text(json.dumps({
            "scenario_title": "Tool trajectory git",
            "verdict": "FAIL",
            "primary_verdict": "FAIL",
            "turn_count": 2,
            "tool_histogram": {"git_status": 1, "edit_file": 2},
            "changed_files": ["math_utils.py"],
            "infra_signals": ["rate_limit_detected"],
            "agent_fail_signals": ["trajectory_assertions_failed"],
        }))
        (run_dir / "tool_calls.jsonl").write_text('{"tool_name": "edit_file"}\n')
        (run_dir / "turns.json").write_text(json.dumps([{"turn": 1}, {"turn": 2}]))
        (run_dir / "trajectory_report.json").write_text(json.dumps({"passed": False}))
        (run_dir / "turn_report.json").write_text(json.dumps({"passed": True, "results": []}))
        (run_dir / "artifact_report.json").write_text(json.dumps({"passed": True, "results": []}))
        (run_dir / "grading_report.json").write_text(json.dumps({"verdict": "FAIL"}))

        summary = scan_run(run_dir)
        assert summary.verdict == "FAIL"
        assert summary.primary_verdict == "FAIL"
        assert summary.tool_histogram["git_status"] == 1
        assert "math_utils.py" in summary.changed_files
        assert summary.infra_signals == ["rate_limit_detected"]
        assert summary.agent_fail_signals == ["trajectory_assertions_failed"]
        assert summary.missing_artifacts == []

    def test_summarize_all_aggregates(self, tmp_path: Path):
        from benchmarks.ai_verification.summarize_runs import summarize_all

        for run_id, verdict in [("run1", "PASS"), ("run2", "FAIL"), ("run3", "PASS")]:
            rd = tmp_path / run_id
            rd.mkdir()
            (rd / "meta.json").write_text(json.dumps({"run_id": run_id, "status": verdict, "wall_time_s": 50.0}))
            (rd / "run_summary.json").write_text(json.dumps({"verdict": verdict}))
            (rd / "tool_calls.jsonl").write_text("")
            (rd / "turns.json").write_text("[]")
            (rd / "trajectory_report.json").write_text(json.dumps({"passed": True}))
            (rd / "turn_report.json").write_text(json.dumps({"passed": True, "results": []}))
            (rd / "artifact_report.json").write_text(json.dumps({"passed": True, "results": []}))
            (rd / "grading_report.json").write_text(json.dumps({"verdict": verdict}))

        result = summarize_all(tmp_path)
        assert result["total_runs"] == 3
        assert result["verdict_counts"]["PASS"] == 2
        assert result["verdict_counts"]["FAIL"] == 1

    def test_summarize_all_filters_to_selected_run_ids(self, tmp_path: Path):
        from benchmarks.ai_verification.summarize_runs import summarize_all

        for run_id, verdict in [("current-a", "PASS"), ("historical-b", "FAIL")]:
            rd = tmp_path / run_id
            rd.mkdir()
            (rd / "meta.json").write_text(json.dumps({"run_id": run_id, "status": verdict, "wall_time_s": 50.0}))
            (rd / "run_summary.json").write_text(json.dumps({"verdict": verdict}))

        result = summarize_all(tmp_path, run_ids={"current-a"})

        assert result["total_runs"] == 1
        assert result["runs"][0]["run_id"] == "current-a"

    def test_summarize_batch_manifest_limits_to_current_batch(self, tmp_path: Path):
        from benchmarks.ai_verification.summarize_runs import summarize_batch_manifest

        qa_base = tmp_path / "qa"
        qa_base.mkdir()
        for run_id, verdict in [("current-a", "PASS"), ("historical-b", "FAIL")]:
            rd = qa_base / run_id
            rd.mkdir()
            (rd / "meta.json").write_text(json.dumps({"run_id": run_id, "status": verdict, "wall_time_s": 50.0}))
            (rd / "run_summary.json").write_text(json.dumps({"verdict": verdict}))

        manifest = tmp_path / "batch_manifest.json"
        manifest.write_text(json.dumps({
            "runs": [
                {"run_id": "current-a", "run_dir": str(qa_base / "current-a")},
            ],
        }))

        result = summarize_batch_manifest(manifest)

        assert result["total_runs"] == 1
        assert result["runs"][0]["run_id"] == "current-a"

    def test_flags_missing_artifacts(self, tmp_path: Path):
        from benchmarks.ai_verification.summarize_runs import summarize_all

        rd = tmp_path / "incomplete-run"
        rd.mkdir()
        (rd / "meta.json").write_text(json.dumps({"run_id": "incomplete-run", "status": "INFRA_FAIL"}))
        (rd / "grading_report.json").write_text(json.dumps({"verdict": "INFRA_FAIL"}))

        result = summarize_all(tmp_path)
        assert result["total_runs"] == 1
        assert result["runs_with_missing_artifacts"] == 1

    def test_reports_assertion_failures(self, tmp_path: Path):
        from benchmarks.ai_verification.summarize_runs import summarize_all

        rd = tmp_path / "failed-assertions"
        rd.mkdir()
        (rd / "meta.json").write_text(json.dumps({"run_id": "failed-assertions", "status": "FAIL"}))
        (rd / "grading_report.json").write_text(json.dumps({"verdict": "FAIL"}))
        (rd / "run_summary.json").write_text(json.dumps({"verdict": "FAIL"}))
        (rd / "tool_calls.jsonl").write_text("")
        (rd / "turns.json").write_text("[]")
        (rd / "trajectory_report.json").write_text(json.dumps({
            "passed": False,
            "results": [
                {"assertion": "must_use_tools", "passed": False, "detail": "missing tools: ['ask_user']"},
                {"assertion": "min_tool_calls", "passed": False, "detail": "expected >= 1, got 0"},
            ],
        }))

        result = summarize_all(tmp_path)

        assert result["assertion_failures"] == [
            {
                "run_id": "failed-assertions",
                "source": "trajectory_report.json",
                "assertion": "must_use_tools",
                "detail": "missing tools: ['ask_user']",
            },
            {
                "run_id": "failed-assertions",
                "source": "trajectory_report.json",
                "assertion": "min_tool_calls",
                "detail": "expected >= 1, got 0",
            },
        ]


    def test_result_sha256_scrubs_secrets(self):
        from benchmarks.ai_verification.run_artifacts import build_tool_call_record

        record = build_tool_call_record(
            event_type="tool_call_completed",
            thread_id="t1",
            turn_id="tu1",
            item_id="item-1",
            tool_call_id="call-1",
            tool_name="search_text",
            tool_family="search",
            status="success",
            started_at="2026-05-01T00:00:00Z",
            finished_at="2026-05-01T00:00:01Z",
            args={"pattern": "TODO", "api_key": "sk-secret"},
            result={"data": "found", "access_token": "tok-123"},
        )
        assert record["result_sha256"] != ""

    def test_scrubs_variant_key_names(self):
        from benchmarks.ai_verification.run_artifacts import _scrub_secrets

        data = {"access_token": "tok", "refreshToken": "tok2", "github_token": "gh-abc"}
        result = _scrub_secrets(data)
        assert result["access_token"] == "<redacted>"
        assert result["refreshToken"] == "<redacted>"
        assert result["github_token"] == "<redacted>"


class TestValidateFixtureVerdict:
    def test_validate_fixture_writes_neutral_trajectory_and_turn_reports(self):
        from benchmarks.ai_verification.scenario_yaml import load_scenario_yaml
        from benchmarks.ai_verification.run_scenario import run

        yaml_text = textwrap.dedent("""\
            title: Neutral artifact fixture
            category: backend_feature
            difficulty: easy
            target_stack:
              language: python
            task_spec:
              prompt: "Do something"
            grading:
              checks:
                - snapshot
              check_commands:
                snapshot: "true"
        """)
        spec = load_scenario_yaml(yaml_text)

        import tempfile

        with tempfile.TemporaryDirectory() as tmp_qa:
            qa_base = Path(tmp_qa)
            run_id, report = run(
                scenario_path=_write_temp_scenario(spec),
                validate_fixture=True,
                qa_base=qa_base,
            )

            run_dir = qa_base / run_id
            trajectory = json.loads((run_dir / "trajectory_report.json").read_text())
            turn = json.loads((run_dir / "turn_report.json").read_text())

        assert report.verdict.value == "PASS"
        assert trajectory == {"passed": True, "results": []}
        assert turn == {"passed": True, "results": []}

    def test_backend_feature_validate_fixture_defaults_to_clean_pass(self):
        from benchmarks.ai_verification.scenario_yaml import load_scenario_yaml
        from benchmarks.ai_verification.schema import Verdict
        from benchmarks.ai_verification.run_scenario import run

        yaml_text = textwrap.dedent("""\
            title: Backend feature fixture clean
            category: backend_feature
            difficulty: easy
            target_stack:
              language: python
            task_spec:
              prompt: "Do something"
            grading:
              checks:
                - snapshot
              check_commands:
                snapshot: "true"
        """)
        spec = load_scenario_yaml(yaml_text)

        import tempfile

        with tempfile.TemporaryDirectory() as tmp_qa:
            run_id, report = run(
                scenario_path=_write_temp_scenario(spec),
                validate_fixture=True,
                qa_base=Path(tmp_qa),
            )

        assert run_id
        assert report.verdict == Verdict.PASS

    def test_expected_failure_fixture_warning_names_actual_category(self, capsys):
        from benchmarks.ai_verification.scenario_yaml import load_scenario_yaml
        from benchmarks.ai_verification.schema import Verdict
        from benchmarks.ai_verification.run_scenario import run

        yaml_text = textwrap.dedent("""\
            title: Repo init fixture unexpectedly clean
            category: repo_init
            difficulty: easy
            target_stack:
              language: python
            task_spec:
              prompt: "Do something"
            grading:
              checks:
                - snapshot
              check_commands:
                snapshot: "true"
        """)
        spec = load_scenario_yaml(yaml_text)

        import tempfile

        with tempfile.TemporaryDirectory() as tmp_qa:
            run_id, report = run(
                scenario_path=_write_temp_scenario(spec),
                validate_fixture=True,
                qa_base=Path(tmp_qa),
            )

        captured = capsys.readouterr()
        assert run_id
        assert report.verdict == Verdict.FAIL
        assert "repo_init fixture started CLEAN" in captured.out
        assert "dirty_cleanup fixture started CLEAN" not in captured.out

    def test_validate_fixture_with_artifact_fail_forces_fail(self):
        from benchmarks.ai_verification.scenario_yaml import load_scenario_yaml
        from benchmarks.ai_verification.schema import Verdict
        from benchmarks.ai_verification.run_scenario import run

        yaml_text = textwrap.dedent("""\
            title: Fixture artifact fail test
            category: backend_feature
            difficulty: easy
            target_stack:
              language: python
            task_spec:
              prompt: "Do something"
            expected_outcomes:
              must_have: []
            grading:
              checks:
                - snapshot
              check_commands:
                snapshot: "true"
            artifact_assertions:
              forbid_noop_pass: true
              require_non_empty_diff: true
        """)
        spec = load_scenario_yaml(yaml_text)

        from unittest.mock import patch
        import tempfile

        with tempfile.TemporaryDirectory() as tmp_qa:
            qa_base = Path(tmp_qa)
            with patch("benchmarks.ai_verification.run_scenario._run_autocode", return_value=(0, 0, 100, 50, [], "", [])):
                run_id, report = run(
                    scenario_path=_write_temp_scenario(spec),
                    validate_fixture=True,
                    qa_base=qa_base,
                )
            assert report.verdict == Verdict.FAIL


class TestToolCallStartedEmission:
    def test_started_event_emitted_before_completed(self):
        from autocode.backend.headless_schema import validate_event

        import io
        from autocode.backend.headless_runner import HeadlessRunner

        buf = io.StringIO()
        runner = HeadlessRunner.__new__(HeadlessRunner)
        runner._output = buf
        runner._thread_id = "t1"
        runner._turn_id = "tu1"
        runner._item_counter = 0

        runner._emit_tool_call({
            "name": "search_text",
            "status": "success",
            "result": "found 3",
            "call_id": "call-1",
        })

        lines = buf.getvalue().strip().splitlines()
        types = []
        for line in lines:
            ev = validate_event(json.loads(line))
            types.append(ev.type)

        assert "tool_call_started" in types
        assert "tool_call_completed" in types
        started_idx = types.index("tool_call_started")
        completed_idx = types.index("tool_call_completed")
        assert started_idx < completed_idx


class TestRequiredToolEventFields:
    def test_started_rejects_empty_tool_name(self):
        from autocode.backend.headless_schema import validate_event

        with pytest.raises(Exception, match="tool_name"):
            validate_event({
                "protocol_version": "0.2.0-harness",
                "type": "tool_call_started",
                "tool_call_id": "call-1",
                "started_at": "2026-05-01T00:00:00Z",
            })

    def test_started_rejects_empty_call_id(self):
        from autocode.backend.headless_schema import validate_event

        with pytest.raises(Exception, match="tool_call_id"):
            validate_event({
                "protocol_version": "0.2.0-harness",
                "type": "tool_call_started",
                "tool_name": "search_text",
                "started_at": "2026-05-01T00:00:00Z",
            })

    def test_started_rejects_empty_started_at(self):
        from autocode.backend.headless_schema import validate_event

        with pytest.raises(Exception, match="started_at"):
            validate_event({
                "protocol_version": "0.2.0-harness",
                "type": "tool_call_started",
                "tool_name": "search_text",
                "tool_call_id": "call-1",
            })

    def test_completed_rejects_empty_finished_at(self):
        from autocode.backend.headless_schema import validate_event

        with pytest.raises(Exception, match="finished_at"):
            validate_event({
                "protocol_version": "0.2.0-harness",
                "type": "tool_call_completed",
                "tool_name": "search_text",
                "tool_call_id": "call-1",
                "started_at": "2026-05-01T00:00:00Z",
                "status": "success",
            })

    def test_failed_rejects_empty_finished_at(self):
        from autocode.backend.headless_schema import validate_event

        with pytest.raises(Exception, match="finished_at"):
            validate_event({
                "protocol_version": "0.2.0-harness",
                "type": "tool_call_failed",
                "tool_name": "run_command",
                "tool_call_id": "call-1",
                "started_at": "2026-05-01T00:00:00Z",
                "error_type": "TimeoutError",
                "error_message": "timeout",
            })


class TestMustRemoveTextFinalFiles:
    def test_must_remove_text_checks_final_file(self, tmp_path: Path):
        from benchmarks.ai_verification.artifact_grader import grade_artifacts

        (tmp_path / "config.py").write_text("API_KEY = 'still-here'\nDEBUG = True\n")
        report = grade_artifacts(
            diff_patch="diff --git a/config.py b/config.py\n-API_KEY = old\n+API_KEY = 'still-here'\n",
            changed_files=["config.py"],
            sandbox=tmp_path,
            assertions={"must_remove_text": ["API_KEY"]},
        )
        assert not report.passed

    def test_must_remove_text_passes_when_removed(self, tmp_path: Path):
        from benchmarks.ai_verification.artifact_grader import grade_artifacts

        (tmp_path / "config.py").write_text("DEBUG = True\n")
        report = grade_artifacts(
            diff_patch="diff --git a/config.py b/config.py\n-API_KEY = old\n",
            changed_files=["config.py"],
            sandbox=tmp_path,
            assertions={"must_remove_text": ["API_KEY"]},
        )
        assert report.passed

    def test_must_remove_text_file_scoped(self, tmp_path: Path):
        from benchmarks.ai_verification.artifact_grader import grade_artifacts

        (tmp_path / "config.py").write_text("API_KEY = 'x'\n")
        (tmp_path / "other.py").write_text("API_KEY = 'y'\n")
        report = grade_artifacts(
            diff_patch="",
            changed_files=["config.py"],
            sandbox=tmp_path,
            assertions={"must_remove_text": [{"file": "config.py", "text": "API_KEY"}]},
        )
        assert not report.passed

    def test_must_remove_text_file_scoped_passes(self, tmp_path: Path):
        from benchmarks.ai_verification.artifact_grader import grade_artifacts

        (tmp_path / "config.py").write_text("DEBUG = True\n")
        (tmp_path / "other.py").write_text("API_KEY = 'y'\n")
        report = grade_artifacts(
            diff_patch="",
            changed_files=["config.py"],
            sandbox=tmp_path,
            assertions={"must_remove_text": [{"file": "config.py", "text": "API_KEY"}]},
        )
        assert report.passed

    def test_extract_changed_files_ignores_generated_pyc_noise(self):
        from benchmarks.ai_verification.artifact_grader import extract_changed_files

        diff_patch = "\n".join([
            "diff --git a/__pycache__/processor.cpython-312.pyc b/__pycache__/processor.cpython-312.pyc",
            "diff --git a/processor.py b/processor.py",
        ])

        assert extract_changed_files(diff_patch) == ["processor.py"]


class TestDocsMentionArtifacts:
    def test_harness_runner_instructions_mentions_new_artifacts(self):
        content = (PROJECT_ROOT / "benchmarks" / "ai_verification" / "HARNESS_RUNNER_INSTRUCTIONS.md").read_text()
        assert "tool_calls.jsonl" in content
        assert "run_summary.json" in content
        assert "trajectory_report.json" in content
        assert "Verdict Composition Table" in content

    def test_multiturn_guide_mentions_protocol_version(self):
        content = (PROJECT_ROOT / "benchmarks" / "ai_verification" / "MULTITURN_GUIDE.md").read_text()
        assert "0.2.0-harness" in content
        assert "Live Provider Canaries" in content

    def test_multiturn_guide_explains_turn_artifacts_and_regression_semantics(self):
        content = (PROJECT_ROOT / "benchmarks" / "ai_verification" / "MULTITURN_GUIDE.md").read_text()
        for required in (
            "turns.json",
            "turn_report.json",
            "run_summary.json",
            "no_regression_after_pass",
            "pass-then-regress",
            "trajectory_report.json",
        ):
            assert required in content
