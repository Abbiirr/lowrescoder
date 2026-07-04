"""P1 AI Verification Harness Narrow Substrate — RED tests.

Tests for:
  - YAML scenario loading (scenario_yaml.py)
  - NDJSON runner (ndjson_runner.py)
  - NDJSON grader (ndjson_grader.py)
  - Sandbox isolation
  - Runner determinism

These tests MUST fail (RED) before any implementation code is written.
They validate the P1 narrow substrate using EXISTING features only:
  - benchmarks/ai_verification/schema.py (ScenarioSpec, etc.)
  - autocode exec --json (C6.G5 NDJSON)
  - autocode/src/autocode/backend/headless_schema.py (event types)
  - benchmarks/ai_verification/sandbox_builder.py
"""

from __future__ import annotations

import json
import sys
import textwrap
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------------------------
# YAML Scenario Loader
# ---------------------------------------------------------------------------


class TestYamlScenarioLoader:
    def test_load_minimal_yaml_to_scenario_spec(self):
        from benchmarks.ai_verification.scenario_yaml import load_scenario_yaml

        yaml_text = textwrap.dedent("""\
            title: Simple edit
            category: backend_feature
            difficulty: easy
            target_stack:
              language: python
            task_spec:
              prompt: "Edit hello.py to return 'world'"
            expected_outcomes:
              must_have:
                - "item_completed event present"
              must_not_have:
                - "error event"
        """)
        spec = load_scenario_yaml(yaml_text)
        assert spec.title == "Simple edit"
        assert spec.category.value == "backend_feature"
        assert spec.task_spec.prompt == "Edit hello.py to return 'world'"

    def test_yaml_expected_outcomes_preserved(self):
        from benchmarks.ai_verification.scenario_yaml import load_scenario_yaml

        yaml_text = textwrap.dedent("""\
            title: Cost routing
            category: backend_feature
            difficulty: medium
            target_stack:
              language: python
            task_spec:
              prompt: "Check cost routing"
            expected_outcomes:
              must_have:
                - "turn_completed event with usage"
                - "item_started with kind=tool_execution"
              must_not_have:
                - "error event"
                - "item_started with kind=unknown"
        """)
        spec = load_scenario_yaml(yaml_text)
        assert len(spec.expected_outcomes["must_have"]) == 2
        assert len(spec.expected_outcomes["must_not_have"]) == 2

    def test_yaml_without_expected_outcomes_defaults_empty(self):
        from benchmarks.ai_verification.scenario_yaml import load_scenario_yaml

        yaml_text = textwrap.dedent("""\
            title: Minimal
            category: backend_feature
            difficulty: easy
            target_stack:
              language: python
            task_spec:
              prompt: "Do something"
        """)
        spec = load_scenario_yaml(yaml_text)
        assert spec.expected_outcomes == {"must_have": [], "must_not_have": []}

    def test_yaml_followup_prompts_are_preserved(self):
        from benchmarks.ai_verification.scenario_yaml import load_scenario_yaml

        yaml_text = textwrap.dedent("""\
            title: Multi-turn loader
            category: backend_feature
            difficulty: easy
            target_stack:
              language: python
            task_spec:
              prompt: "Turn one"
              followup_prompts:
                - "Turn two"
                - "Turn three"
        """)

        spec = load_scenario_yaml(yaml_text)

        assert spec.task_spec.followup_prompts == ["Turn two", "Turn three"]

    def test_yaml_repo_seed_files_become_injections(self):
        from benchmarks.ai_verification.scenario_yaml import load_scenario_yaml

        yaml_text = textwrap.dedent("""\
            title: Files loader
            category: backend_feature
            difficulty: easy
            target_stack:
              language: python
            task_spec:
              prompt: "Use seeded files"
            repo_seed:
              mode: fresh
              files:
                app.py: |
                  print("hello")
                tests/test_app.py: |
                  def test_app():
                      assert True
        """)

        spec = load_scenario_yaml(yaml_text)

        injected = {item.path: item.content for item in spec.repo_seed.injections}
        assert injected["app.py"].strip() == 'print("hello")'
        assert "def test_app" in injected["tests/test_app.py"]

    def test_scenario_spec_load_accepts_yaml_files(self, tmp_path: Path):
        from benchmarks.ai_verification.schema import ScenarioSpec

        scenario_path = tmp_path / "scenario.yaml"
        scenario_path.write_text(textwrap.dedent("""\
            title: YAML file load
            category: backend_feature
            difficulty: easy
            target_stack:
              language: python
            task_spec:
              prompt: "Check loader"
        """))

        spec = ScenarioSpec.load(scenario_path)

        assert spec.title == "YAML file load"


# ---------------------------------------------------------------------------
# Supervised live runner
# ---------------------------------------------------------------------------


class TestSupervisedRunScenario:
    def test_default_retry_schedule_matches_long_infra_recovery_window(self):
        from benchmarks.ai_verification.run_scenario_supervised import (
            DEFAULT_RETRY_SCHEDULE_SECONDS,
            parse_retry_schedule,
        )

        expected = [
            5,
            30,
            60,
            120,
            180,
            240,
            300,
            360,
            420,
            480,
            540,
            600,
            1200,
            1800,
            3600,
            7200,
            10800,
            14400,
            18000,
            21600,
            25200,
            28800,
            32400,
            36000,
        ]

        assert DEFAULT_RETRY_SCHEDULE_SECONDS == expected
        assert parse_retry_schedule("5s,30s,1m,2m,10m,1h,10h") == [
            5,
            30,
            60,
            120,
            600,
            3600,
            36000,
        ]

        total_with_600s_attempt_timeout = (
            sum(DEFAULT_RETRY_SCHEDULE_SECONDS)
            + (len(DEFAULT_RETRY_SCHEDULE_SECONDS) + 1) * 600
        )
        assert total_with_600s_attempt_timeout > 57 * 60 * 60

    def test_default_retry_policy_retries_transient_infra_until_pass(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ):
        from benchmarks.ai_verification import run_scenario_supervised as supervisor

        scenario_path = tmp_path / "scenario.yaml"
        scenario_path.write_text(textwrap.dedent("""\
            title: Retry until pass
            category: backend_feature
            difficulty: easy
            target_stack:
              language: python
            task_spec:
              prompt: "Do something"
        """))
        qa_base = tmp_path / "qa"
        report_base = tmp_path / "reports"
        calls: list[int] = []
        sleeps: list[int] = []

        def fake_run_supervised(**kwargs):
            calls.append(len(calls) + 1)
            verdict = "INFRA_FAIL" if len(calls) == 1 else "PASS"
            reason = "provider timeout" if verdict == "INFRA_FAIL" else "child completed with verdict PASS"
            run_id = f"run-{len(calls)}"
            run_dir = qa_base / run_id
            run_dir.mkdir(parents=True, exist_ok=True)
            (run_dir / "run_summary.json").write_text(json.dumps({"verdict": verdict}))
            report_dir = report_base / f"attempt-{len(calls)}"
            report_dir.mkdir(parents=True, exist_ok=True)
            return supervisor.SupervisedRunReport(
                scenario=str(scenario_path),
                agent="autocode",
                command=["child"],
                timed_out=verdict == "INFRA_FAIL",
                exit_code=124 if verdict == "INFRA_FAIL" else 0,
                final_run_id=run_id,
                final_run_dir=str(run_dir),
                final_verdict=verdict,
                reason=reason,
                output_log=str(report_dir / "supervisor_output.log"),
                report_dir=str(report_dir),
            )

        monkeypatch.setattr(supervisor, "run_supervised", fake_run_supervised)
        monkeypatch.setattr(supervisor.time, "sleep", lambda delay: sleeps.append(int(delay)))

        report = supervisor.run_supervised_with_retries(
            command=["child"],
            scenario_path=scenario_path,
            agent="autocode",
            qa_base=qa_base,
            report_base=report_base,
            timeout_seconds=600,
            retry_schedule_seconds=[5, 30],
        )

        assert report.final_verdict == "PASS"
        assert calls == [1, 2]
        assert sleeps == [5]

        retry_report = json.loads((Path(report.report_dir) / "retry_report.json").read_text())
        assert retry_report["final_verdict"] == "PASS"
        assert retry_report["attempt_count"] == 2
        assert retry_report["attempts"][0]["verdict"] == "INFRA_FAIL"
        assert retry_report["attempts"][0]["next_delay_s"] == 5
        assert retry_report["attempts"][1]["verdict"] == "PASS"
        assert retry_report["attempts"][1]["next_delay_s"] == 0

    def test_timeout_completes_partial_run_as_infra_fail(self, tmp_path: Path):
        from benchmarks.ai_verification.run_scenario_supervised import run_supervised

        scenario_path = tmp_path / "scenario.yaml"
        scenario_path.write_text(textwrap.dedent("""\
            title: Supervised timeout
            category: backend_feature
            difficulty: easy
            target_stack:
              language: python
            task_spec:
              prompt: "Do something"
            trajectory_assertions:
              min_tool_calls: 1
            turn_assertions:
              min_turns: 1
        """))
        qa_base = tmp_path / "qa"
        run_id = "20260502-testtimeout"
        child = textwrap.dedent(f"""\
            import json
            import pathlib
            import shutil
            import time

            scenario = pathlib.Path({str(scenario_path)!r})
            run_dir = pathlib.Path({str(qa_base)!r}) / {run_id!r}
            run_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(scenario, run_dir / "scenario.json")
            print("[run_scenario] run_id={run_id}", flush=True)
            time.sleep(30)
        """)

        report = run_supervised(
            command=[sys.executable, "-c", child],
            scenario_path=scenario_path,
            agent="autocode",
            qa_base=qa_base,
            report_base=tmp_path / "reports",
            timeout_seconds=1,
        )

        run_dir = qa_base / run_id
        assert report.final_verdict == "INFRA_FAIL"
        assert report.final_run_id == run_id
        assert json.loads((run_dir / "grading_report.json").read_text())["verdict"] == "INFRA_FAIL"
        assert json.loads((run_dir / "meta.json").read_text())["infra_fail_reason"]
        assert json.loads((run_dir / "run_summary.json").read_text())["trajectory_satisfied"] is False
        assert (run_dir / "tool_calls.jsonl").read_text() == ""
        assert json.loads((run_dir / "turns.json").read_text()) == []
        assert json.loads((run_dir / "trajectory_report.json").read_text())["passed"] is False
        assert json.loads((run_dir / "turn_report.json").read_text())["passed"] is False

    def test_completed_child_does_not_overwrite_verdict(self, tmp_path: Path):
        from benchmarks.ai_verification.run_scenario_supervised import run_supervised

        scenario_path = tmp_path / "scenario.yaml"
        scenario_path.write_text(textwrap.dedent("""\
            title: Supervised completed
            category: backend_feature
            difficulty: easy
            target_stack:
              language: python
            task_spec:
              prompt: "Do something"
        """))
        qa_base = tmp_path / "qa"
        run_id = "20260502-testpass"
        child = textwrap.dedent(f"""\
            import json
            import pathlib
            import shutil

            scenario = pathlib.Path({str(scenario_path)!r})
            run_dir = pathlib.Path({str(qa_base)!r}) / {run_id!r}
            run_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(scenario, run_dir / "scenario.json")
            (run_dir / "grading_report.json").write_text(json.dumps({{"verdict": "PASS", "check_results": []}}))
            (run_dir / "meta.json").write_text(json.dumps({{"run_id": {run_id!r}, "status": "PASS"}}))
            (run_dir / "run_summary.json").write_text(json.dumps({{"run_id": {run_id!r}, "verdict": "PASS"}}))
            print("[run_scenario] run_id={run_id}", flush=True)
        """)

        report = run_supervised(
            command=[sys.executable, "-c", child],
            scenario_path=scenario_path,
            agent="autocode",
            qa_base=qa_base,
            report_base=tmp_path / "reports",
            timeout_seconds=10,
        )

        assert report.final_verdict == "PASS"
        assert json.loads((qa_base / run_id / "grading_report.json").read_text())["verdict"] == "PASS"

    def test_child_without_readable_verdict_completes_infra_fail_artifacts(self, tmp_path: Path):
        from benchmarks.ai_verification.run_scenario_supervised import run_supervised

        scenario_path = tmp_path / "scenario.yaml"
        scenario_path.write_text(textwrap.dedent("""\
            title: Missing child verdict
            category: backend_feature
            difficulty: easy
            target_stack:
              language: python
            task_spec:
              prompt: "Do something"
        """))
        qa_base = tmp_path / "qa"
        run_id = "20260502-missingverdict"
        child = textwrap.dedent(f"""\
            import pathlib
            import shutil

            scenario = pathlib.Path({str(scenario_path)!r})
            run_dir = pathlib.Path({str(qa_base)!r}) / {run_id!r}
            run_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(scenario, run_dir / "scenario.json")
            print("[run_scenario] run_id={run_id}", flush=True)
        """)

        report = run_supervised(
            command=[sys.executable, "-c", child],
            scenario_path=scenario_path,
            agent="autocode",
            qa_base=qa_base,
            report_base=tmp_path / "reports",
            timeout_seconds=10,
        )

        run_dir = qa_base / run_id
        assert report.final_verdict == "INFRA_FAIL"
        assert "without a readable grading verdict" in report.reason
        assert json.loads((run_dir / "grading_report.json").read_text())["verdict"] == "INFRA_FAIL"
        assert json.loads((run_dir / "run_summary.json").read_text())["verdict"] == "INFRA_FAIL"
        assert json.loads((run_dir / "meta.json").read_text())["infra_fail_reason"]
        assert json.loads((run_dir / "trajectory_report.json").read_text())["passed"] is True
        assert json.loads((run_dir / "turn_report.json").read_text())["passed"] is True
        assert json.loads((run_dir / "artifact_report.json").read_text())["passed"] is True

    def test_discover_scenarios_supports_directory_and_multiturn_tag(self):
        from benchmarks.ai_verification.run_scenario_supervised import discover_scenarios

        scenarios = discover_scenarios(
            PROJECT_ROOT / "benchmarks" / "ai_verification" / "scenarios",
            tag="multiturn",
        )

        names = [path.name for path in scenarios]
        assert "multi-turn-regression.yaml" in names
        assert names == sorted(names)
        assert all("followup_prompts:" in path.read_text() for path in scenarios)

    def test_batch_supervision_continues_after_infra_fail(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ):
        from benchmarks.ai_verification import run_scenario_supervised as supervisor

        scenario_dir = tmp_path / "scenarios"
        scenario_dir.mkdir()
        for name in ("first.yaml", "second.yaml"):
            (scenario_dir / name).write_text(textwrap.dedent(f"""\
                title: {name}
                category: backend_feature
                difficulty: easy
                target_stack:
                  language: python
                task_spec:
                  prompt: "Do {name}"
            """))

        qa_base = tmp_path / "qa"
        report_base = tmp_path / "reports"
        calls: list[str] = []

        def fake_run_supervised_with_retries(**kwargs):
            scenario_path = Path(kwargs["scenario_path"])
            calls.append(scenario_path.name)
            verdict = "INFRA_FAIL" if scenario_path.name == "first.yaml" else "PASS"
            run_id = f"run-{scenario_path.stem}"
            run_dir = qa_base / run_id
            run_dir.mkdir(parents=True, exist_ok=True)
            (run_dir / "run_summary.json").write_text(
                json.dumps({"run_id": run_id, "verdict": verdict}) + "\n",
            )
            report_dir = report_base / f"{scenario_path.stem}-supervised"
            report_dir.mkdir(parents=True, exist_ok=True)
            return supervisor.SupervisedRunReport(
                scenario=str(scenario_path),
                agent="autocode",
                command=["child"],
                timed_out=verdict == "INFRA_FAIL",
                exit_code=124 if verdict == "INFRA_FAIL" else 0,
                final_run_id=run_id,
                final_run_dir=str(run_dir),
                final_verdict=verdict,
                reason=f"child completed with verdict {verdict}",
                output_log=str(report_dir / "supervisor_output.log"),
                report_dir=str(report_dir),
            )

        monkeypatch.setattr(
            supervisor,
            "run_supervised_with_retries",
            fake_run_supervised_with_retries,
        )

        batch = supervisor.run_batch_supervised(
            scenario_input=scenario_dir,
            tag=None,
            agent="autocode",
            qa_base=qa_base,
            report_base=report_base,
            timeout_seconds=10,
            retry_schedule_seconds=[],
        )

        assert calls == ["first.yaml", "second.yaml"]
        assert batch.exit_code == 1
        assert batch.verdict_counts == {"INFRA_FAIL": 1, "PASS": 1}
        manifest = json.loads((Path(batch.batch_dir) / "batch_manifest.json").read_text())
        assert manifest["scenario_count"] == 2
        assert manifest["verdict_counts"] == {"INFRA_FAIL": 1, "PASS": 1}
        assert [run["scenario_name"] for run in manifest["runs"]] == ["first.yaml", "second.yaml"]

    def test_yaml_invalid_category_raises(self):
        from benchmarks.ai_verification.scenario_yaml import load_scenario_yaml

        yaml_text = textwrap.dedent("""\
            title: Bad
            category: not_a_real_category
            difficulty: easy
            target_stack:
              language: python
            task_spec:
              prompt: "x"
        """)
        with pytest.raises(ValueError, match="category"):
            load_scenario_yaml(yaml_text)


# ---------------------------------------------------------------------------
# NDJSON Runner
# ---------------------------------------------------------------------------


class TestNdjsonRunner:
    def test_parse_ndjson_stream_extracts_events(self):
        from benchmarks.ai_verification.ndjson_runner import parse_ndjson_stream

        raw_lines = [
            json.dumps({"type": "thread_started", "protocol_version": "0.1.0-c6g5-subset", "thread_id": "t1"}),
            json.dumps({"type": "turn_started", "protocol_version": "0.1.0-c6g5-subset", "turn_id": "tu1", "thread_id": "t1", "message": "hello"}),
            json.dumps({"type": "turn_completed", "protocol_version": "0.1.0-c6g5-subset", "turn_id": "tu1", "thread_id": "t1", "usage": {"input_tokens": 100, "output_tokens": 50}}),
        ]
        events = parse_ndjson_stream(raw_lines)
        assert len(events) == 3
        assert events[0].type == "thread_started"
        assert events[2].usage.input_tokens == 100

    def test_parse_ndjson_skips_invalid_lines(self):
        from benchmarks.ai_verification.ndjson_runner import parse_ndjson_stream

        raw_lines = [
            "not json at all",
            json.dumps({"type": "thread_started", "protocol_version": "0.1.0-c6g5-subset"}),
            "",
            json.dumps({"type": "error", "protocol_version": "0.1.0-c6g5-subset", "message": "oops"}),
        ]
        events = parse_ndjson_stream(raw_lines)
        assert len(events) == 2

    def test_run_result_extracts_tool_calls(self):
        from benchmarks.ai_verification.ndjson_runner import RunResult

        run_result = RunResult(
            exit_code=0,
            events=[],
            tool_calls=3,
            tokens_in=500,
            tokens_out=200,
            error="",
        )
        assert run_result.tool_calls == 3
        assert run_result.tokens_in == 500

    def test_run_result_from_events_extracts_usage(self):
        from benchmarks.ai_verification.ndjson_runner import build_run_result

        raw_lines = [
            json.dumps({"type": "thread_started", "protocol_version": "0.1.0-c6g5-subset"}),
            json.dumps({"type": "turn_started", "protocol_version": "0.1.0-c6g5-subset", "message": "hi"}),
            json.dumps({"type": "item_started", "protocol_version": "0.1.0-c6g5-subset", "kind": "tool_execution"}),
            json.dumps({"type": "item_completed", "protocol_version": "0.1.0-c6g5-subset"}),
            json.dumps({"type": "turn_completed", "protocol_version": "0.1.0-c6g5-subset", "usage": {"input_tokens": 300, "output_tokens": 150}}),
        ]
        result = build_run_result(raw_lines, exit_code=0)
        assert result.tool_calls == 1
        assert result.tokens_in == 300
        assert result.tokens_out == 150
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# NDJSON Grader
# ---------------------------------------------------------------------------


class TestNdjsonGrader:
    def _make_events(self, *types_and_fields):
        lines = []
        for entry in types_and_fields:
            base = {"protocol_version": "0.1.0-c6g5-subset"}
            base.update(entry)
            lines.append(json.dumps(base))
        return lines

    def test_must_have_all_present_passes(self):
        from benchmarks.ai_verification.ndjson_grader import grade_ndjson

        events_raw = self._make_events(
            {"type": "thread_started"},
            {"type": "item_completed"},
        )
        result = grade_ndjson(
            events_raw,
            must_have=["item_completed event present"],
            must_not_have=[],
        )
        assert result.passed is True

    def test_must_have_missing_fails(self):
        from benchmarks.ai_verification.ndjson_grader import grade_ndjson

        events_raw = self._make_events(
            {"type": "thread_started"},
        )
        result = grade_ndjson(
            events_raw,
            must_have=["item_completed event present"],
            must_not_have=[],
        )
        assert result.passed is False
        assert any("item_completed" in f for f in result.failures)

    def test_must_not_have_present_fails(self):
        from benchmarks.ai_verification.ndjson_grader import grade_ndjson

        events_raw = self._make_events(
            {"type": "thread_started"},
            {"type": "error", "message": "boom"},
        )
        result = grade_ndjson(
            events_raw,
            must_have=[],
            must_not_have=["error event"],
        )
        assert result.passed is False
        assert any("error" in f for f in result.failures)

    def test_must_not_have_absent_passes(self):
        from benchmarks.ai_verification.ndjson_grader import grade_ndjson

        events_raw = self._make_events(
            {"type": "thread_started"},
            {"type": "turn_completed", "usage": {}},
        )
        result = grade_ndjson(
            events_raw,
            must_have=[],
            must_not_have=["error event"],
        )
        assert result.passed is True

    def test_tool_execution_predicate(self):
        from benchmarks.ai_verification.ndjson_grader import grade_ndjson

        events_raw = self._make_events(
            {"type": "item_started", "kind": "tool_execution"},
            {"type": "item_completed"},
        )
        result = grade_ndjson(
            events_raw,
            must_have=["item_started with kind=tool_execution"],
            must_not_have=[],
        )
        assert result.passed is True

    def test_cache_hit_ratio_predicate(self):
        from benchmarks.ai_verification.ndjson_grader import grade_ndjson

        events_raw = self._make_events(
            {
                "type": "turn_completed",
                "usage": {
                    "input_tokens": 1000,
                    "cached_input_tokens": 650,
                    "cache_creation_tokens": 100,
                },
            },
        )
        result = grade_ndjson(
            events_raw,
            must_have=["turn_completed usage cache_hit_ratio>=0.5"],
            must_not_have=[],
        )
        assert result.passed is True

    def test_cache_hit_ratio_predicate_fails_below_threshold(self):
        from benchmarks.ai_verification.ndjson_grader import grade_ndjson

        events_raw = self._make_events(
            {
                "type": "turn_completed",
                "usage": {"input_tokens": 1000, "cached_input_tokens": 200},
            },
        )
        result = grade_ndjson(
            events_raw,
            must_have=["turn_completed usage cache_hit_ratio>=0.5"],
            must_not_have=[],
        )
        assert result.passed is False

    def test_malformed_cache_ratio_predicate_fails_gracefully(self):
        from benchmarks.ai_verification.ndjson_grader import grade_ndjson

        events_raw = self._make_events(
            {
                "type": "turn_completed",
                "usage": {"input_tokens": 1000, "cached_input_tokens": 650},
            },
        )
        result = grade_ndjson(
            events_raw,
            must_have=["turn_completed usage cache_hit_ratio>="],
            must_not_have=[],
        )
        assert result.passed is False
        assert "cache_hit_ratio>=" in result.failures[0]
        assert result.warnings == [
            "WARN: malformed predicate 'turn_completed usage cache_hit_ratio>='"
        ]

    def test_item_completed_result_contains_predicate(self):
        from benchmarks.ai_verification.ndjson_grader import grade_ndjson

        events_raw = self._make_events(
            {
                "type": "item_completed",
                "result": "list_files: completed - [Tool output offloaded — 9000 bytes saved]",
            },
        )
        result = grade_ndjson(
            events_raw,
            must_have=["item_completed result contains [Tool output offloaded"],
            must_not_have=[],
        )
        assert result.passed is True

    def test_item_completed_result_contains_predicate_fails_when_missing(self):
        from benchmarks.ai_verification.ndjson_grader import grade_ndjson

        events_raw = self._make_events(
            {"type": "item_completed", "result": "list_files: completed - inline"},
        )
        result = grade_ndjson(
            events_raw,
            must_have=["item_completed result contains [Tool output offloaded"],
            must_not_have=[],
        )
        assert result.passed is False

    def test_usage_predicate(self):
        from benchmarks.ai_verification.ndjson_grader import grade_ndjson

        events_raw = self._make_events(
            {"type": "turn_completed", "usage": {"input_tokens": 100, "output_tokens": 50}},
        )
        result = grade_ndjson(
            events_raw,
            must_have=["turn_completed event with usage"],
            must_not_have=[],
        )
        assert result.passed is True


# ---------------------------------------------------------------------------
# Sandbox isolation
# ---------------------------------------------------------------------------


class TestSandboxIsolation:
    def test_sandbox_is_temporary_and_isolated(self):
        from benchmarks.ai_verification.sandbox_builder import build_sandbox, teardown_sandbox
        from benchmarks.ai_verification.schema import Injection, RepoSeed, SeedMode

        sandbox = Path("/tmp/test-p1-sandbox-isolation")
        if sandbox.exists():
            import shutil
            shutil.rmtree(sandbox, ignore_errors=True)

        seed = RepoSeed(mode=SeedMode.FRESH, injections=[Injection(path="hello.py", content="print('hi')\n")])
        build_sandbox(seed, sandbox)
        assert (sandbox / "hello.py").exists()
        assert (sandbox / ".git").is_dir()
        teardown_sandbox(sandbox)
        assert not sandbox.exists()

    @pytest.mark.parametrize("path", ["../escape.py", "nested/../../escape.py"])
    def test_build_sandbox_rejects_path_traversal_injection(
        self,
        tmp_path: Path,
        path: str,
    ):
        from benchmarks.ai_verification.sandbox_builder import build_sandbox
        from benchmarks.ai_verification.schema import Injection, RepoSeed, SeedMode

        sandbox = tmp_path / "sandbox"
        seed = RepoSeed(
            mode=SeedMode.FRESH,
            injections=[Injection(path=path, content="escaped = True\n")],
        )

        with pytest.raises(ValueError, match="escapes sandbox"):
            build_sandbox(seed, sandbox)
        assert not (tmp_path / "escape.py").exists()

    def test_build_sandbox_rejects_absolute_injection_path(self, tmp_path: Path):
        from benchmarks.ai_verification.sandbox_builder import build_sandbox
        from benchmarks.ai_verification.schema import Injection, RepoSeed, SeedMode

        outside = tmp_path / "absolute.py"
        seed = RepoSeed(
            mode=SeedMode.FRESH,
            injections=[Injection(path=str(outside), content="escaped = True\n")],
        )

        with pytest.raises(ValueError, match="must be relative"):
            build_sandbox(seed, tmp_path / "sandbox")
        assert not outside.exists()


# ---------------------------------------------------------------------------
# Scenario YAML round-trip
# ---------------------------------------------------------------------------


class TestScenarioYamlRoundTrip:
    def test_yaml_load_produces_valid_scenario_spec(self):
        from benchmarks.ai_verification.scenario_yaml import load_scenario_yaml

        yaml_text = textwrap.dedent("""\
            title: Headless NDJSON probe
            category: backend_feature
            difficulty: easy
            target_stack:
              language: python
            task_spec:
              prompt: "Say hello"
              success_criteria:
                - "agent responds"
            expected_outcomes:
              must_have:
                - "turn_completed event with usage"
              must_not_have:
                - "error event"
            grading:
              checks:
                - run_tests
        """)
        spec = load_scenario_yaml(yaml_text)
        assert spec.grading.checks[0].value == "run_tests"
        assert len(spec.task_spec.success_criteria) == 1
        assert spec.expected_outcomes["must_have"] == ["turn_completed event with usage"]


# ---------------------------------------------------------------------------
# Expected-outcome failure propagation through run_scenario pipeline
# ---------------------------------------------------------------------------


class TestNdjsonGradingIntegration:
    def test_failed_expected_outcomes_produce_fail_verdict(self):
        from benchmarks.ai_verification.run_scenario import run

        yaml_text = textwrap.dedent("""\
            title: Failing NDJSON probe
            category: backend_feature
            difficulty: easy
            target_stack:
              language: python
            task_spec:
              prompt: "Say hello"
            expected_outcomes:
              must_have:
                - "item_completed event present"
              must_not_have:
                - "error event"
            grading:
              checks:
                - snapshot
              check_commands:
                snapshot: "true"
        """)
        from benchmarks.ai_verification.scenario_yaml import load_scenario_yaml
        from benchmarks.ai_verification.schema import Verdict

        spec = load_scenario_yaml(yaml_text)

        from unittest.mock import patch
        from benchmarks.ai_verification.ndjson_runner import RunResult

        mock_result = RunResult(
            exit_code=0,
            events=[],
            tool_calls=0,
            tokens_in=0,
            tokens_out=0,
            error="",
        )
        mock_result._raw_lines = [
            json.dumps({"type": "thread_started", "protocol_version": "0.1.0-c6g5-subset"}),
        ]

        import tempfile
        with tempfile.TemporaryDirectory() as tmp_qa:
            qa_base = Path(tmp_qa)
            with patch("benchmarks.ai_verification.run_scenario._run_autocode", return_value=(0, 0, 0, 0, [], "", mock_result._raw_lines)):
                run_id, report = run(
                    scenario_path=_write_temp_scenario(spec),
                    agent="autocode",
                    qa_base=qa_base,
                )
            assert report.verdict == Verdict.FAIL, f"Expected FAIL but got {report.verdict.value}"

    def test_passed_expected_outcomes_produce_pass_verdict(self):
        from benchmarks.ai_verification.scenario_yaml import load_scenario_yaml
        from benchmarks.ai_verification.schema import Verdict
        from benchmarks.ai_verification.run_scenario import run

        yaml_text = textwrap.dedent("""\
            title: Passing NDJSON probe
            category: backend_feature
            difficulty: easy
            target_stack:
              language: python
            task_spec:
              prompt: "Say hello"
            expected_outcomes:
              must_have:
                - "thread_started event present"
              must_not_have:
                - "error event"
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
            json.dumps({"type": "thread_started", "protocol_version": "0.1.0-c6g5-subset"}),
        ]

        with tempfile.TemporaryDirectory() as tmp_qa:
            qa_base = Path(tmp_qa)
            with patch("benchmarks.ai_verification.run_scenario._run_autocode", return_value=(0, 0, 0, 0, [], "", raw_lines)):
                run_id, report = run(
                    scenario_path=_write_temp_scenario(spec),
                    agent="autocode",
                    qa_base=qa_base,
                )
            assert report.verdict == Verdict.PASS, f"Expected PASS but got {report.verdict.value}"
            meta = json.loads((qa_base / run_id / "meta.json").read_text())
            assert meta["status"] == Verdict.PASS.value

    def test_must_not_have_violation_produces_fail_verdict(self):
        from benchmarks.ai_verification.scenario_yaml import load_scenario_yaml
        from benchmarks.ai_verification.schema import Verdict
        from benchmarks.ai_verification.run_scenario import run

        yaml_text = textwrap.dedent("""\
            title: Error event probe
            category: backend_feature
            difficulty: easy
            target_stack:
              language: python
            task_spec:
              prompt: "Say hello"
            expected_outcomes:
              must_have:
                - "thread_started event present"
              must_not_have:
                - "error event"
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
            json.dumps({"type": "thread_started", "protocol_version": "0.1.0-c6g5-subset"}),
            json.dumps({"type": "error", "protocol_version": "0.1.0-c6g5-subset", "message": "boom"}),
        ]

        with tempfile.TemporaryDirectory() as tmp_qa:
            qa_base = Path(tmp_qa)
            with patch("benchmarks.ai_verification.run_scenario._run_autocode", return_value=(0, 0, 0, 0, [], "", raw_lines)):
                run_id, report = run(
                    scenario_path=_write_temp_scenario(spec),
                    agent="autocode",
                    qa_base=qa_base,
                )
            assert report.verdict == Verdict.FAIL
            meta = json.loads((qa_base / run_id / "meta.json").read_text())
            assert meta["status"] == Verdict.FAIL.value

    def test_passed_expected_outcomes_with_failed_check_records_fail_status(self):
        from benchmarks.ai_verification.scenario_yaml import load_scenario_yaml
        from benchmarks.ai_verification.schema import Verdict
        from benchmarks.ai_verification.run_scenario import run

        yaml_text = textwrap.dedent("""\
            title: Passing NDJSON but failing deterministic check
            category: backend_feature
            difficulty: easy
            target_stack:
              language: python
            task_spec:
              prompt: "Say hello"
            expected_outcomes:
              must_have:
                - "thread_started event present"
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
            json.dumps({"type": "thread_started", "protocol_version": "0.1.0-c6g5-subset"}),
        ]

        with tempfile.TemporaryDirectory() as tmp_qa:
            qa_base = Path(tmp_qa)
            with patch("benchmarks.ai_verification.run_scenario._run_autocode", return_value=(0, 0, 0, 0, [], "", raw_lines)):
                run_id, report = run(
                    scenario_path=_write_temp_scenario(spec),
                    agent="autocode",
                    qa_base=qa_base,
                )
            assert report.verdict == Verdict.FAIL
            meta = json.loads((qa_base / run_id / "meta.json").read_text())
            assert meta["status"] == Verdict.FAIL.value


class TestCompactionPathADeterministic:
    def test_compaction_path_a_check_script_passes(self):
        from benchmarks.ai_verification.checks.check_compaction_path_a import verify_path_a_compaction

        errors = verify_path_a_compaction()
        assert errors == [], f"Path A check failed: {errors}"

    def test_compaction_path_a_scenario_validate_fixture_passes(self):
        from benchmarks.ai_verification.run_scenario import run
        from benchmarks.ai_verification.schema import Verdict

        run_id, report = run(
            scenario_path=PROJECT_ROOT
            / "benchmarks"
            / "ai_verification"
            / "scenarios"
            / "compaction-path-a.yaml",
            validate_fixture=True,
        )
        assert report.verdict == Verdict.PASS, f"Expected PASS but got {report.verdict.value}"
        assert len(report.check_results) > 0, "No check_results — check did not execute"
        assert all(r.passed for r in report.check_results), (
            f"Check results not all passed: {[(r.check.value, r.passed, r.output[:200]) for r in report.check_results]}"
        )

    def test_compaction_path_a_test_log_contains_pass_marker(self):
        import tempfile

        from benchmarks.ai_verification.run_scenario import run
        from benchmarks.ai_verification.schema import Verdict

        with tempfile.TemporaryDirectory() as tmp_qa:
            qa_base = Path(tmp_qa)
            run_id, report = run(
                scenario_path=PROJECT_ROOT
                / "benchmarks"
                / "ai_verification"
                / "scenarios"
                / "compaction-path-a.yaml",
                validate_fixture=True,
                qa_base=qa_base,
            )
            assert report.verdict == Verdict.PASS, f"Expected PASS but got {report.verdict.value}"
            assert all(r.passed for r in report.check_results), "Check results not all passed"

            test_log = (qa_base / run_id / "test_log.txt").read_text()
            assert "PASS: Path A compaction deterministic proof succeeded" in test_log, (
                f"test_log.txt does not contain PASS marker. Contents:\n{test_log}"
            )
            assert "can't open file" not in test_log, (
                f"test_log.txt contains file-not-found error. Contents:\n{test_log}"
            )
            assert "No module named" not in test_log, (
                f"test_log.txt contains module-not-found error. Contents:\n{test_log}"
            )

    def test_compaction_path_a_standalone_grade_run_reexecutes_check(self):
        import tempfile

        from benchmarks.ai_verification.grade_run import grade
        from benchmarks.ai_verification.run_scenario import run
        from benchmarks.ai_verification.sandbox_builder import teardown_sandbox
        from benchmarks.ai_verification.schema import Verdict, sandbox_dir

        run_id = ""
        with tempfile.TemporaryDirectory() as tmp_qa:
            qa_base = Path(tmp_qa)
            try:
                run_id, initial_report = run(
                    scenario_path=PROJECT_ROOT
                    / "benchmarks"
                    / "ai_verification"
                    / "scenarios"
                    / "compaction-path-a.yaml",
                    validate_fixture=True,
                    keep_sandbox=True,
                    qa_base=qa_base,
                )
                assert initial_report.verdict == Verdict.PASS

                regrade_report = grade(run_id, base=qa_base, ai_review=False)

                assert regrade_report.verdict == Verdict.PASS
                assert all(r.passed for r in regrade_report.check_results)
                output = "\n".join(r.output for r in regrade_report.check_results)
                assert "PASS: Path A compaction deterministic proof succeeded" in output
                assert "No module named" not in output
            finally:
                if run_id:
                    teardown_sandbox(sandbox_dir(run_id))


def _write_temp_scenario(spec) -> Path:
    import tempfile
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    spec.save(Path(f.name))
    f.close()
    return Path(f.name)
