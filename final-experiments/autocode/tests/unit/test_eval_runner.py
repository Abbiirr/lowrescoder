"""Tests for P3d production eval runner substrate."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals.runner import (  # noqa: E402
    EvalAgentCommand,
    EvalCase,
    EvalRunInput,
    EvalRunner,
    load_cases,
    select_stratified_sample,
)


def test_eval_case_load_from_yaml(tmp_path):
    case_path = tmp_path / "case.yaml"
    case_path.write_text(
        """
id: sample
name: Sample case
provenance: {source: p1, bug_id: bug-1, recorded_at: "2026-05-04"}
setup:
  fixture_repo: ""
  initial_files:
    app.py: "print('hi')\\n"
input: {user_message: "fix it"}
expected_outcomes:
  must_have: ["turn_completed"]
  must_not_have: ["error"]
  judge_criteria: ["correctness"]
config: {model: coding, max_turns: 3, timeout_sec: 120, temperature: 0.0, seed: 0}
baseline:
  correctness_score: 0.9
  minimality_score: 0.8
  test_quality_score: 0.7
  cost_usd_p50: 0.1
""",
        encoding="utf-8",
    )

    case = EvalCase.load(case_path)

    assert case.id == "sample"
    assert case.setup.initial_files["app.py"] == "print('hi')\n"
    assert case.baseline.correctness_score == 0.9


def test_eval_runner_fixture_setup_is_isolated(tmp_path):
    case = EvalCase.load("evals/cases/hfix-refactor-noop-guard.yaml")
    runner = EvalRunner()

    workdir = runner.setup_fixture(case)

    assert workdir != tmp_path
    assert (workdir / "src/example.py").read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_eval_runner_must_have_and_must_not_have_predicates_pass():
    case = EvalCase.load("evals/cases/p1-compaction-path-a.yaml")
    runner = EvalRunner()

    result = await runner.run(
        case,
        EvalRunInput(
            telemetry_events=[
                {"kind": "compaction_event"},
                {"kind": "turn_completed"},
            ],
        ),
    )

    assert result.passed
    assert result.must_have_missing == []
    assert result.must_not_have_present == []


@pytest.mark.asyncio
async def test_eval_runner_must_not_have_violation_fails():
    case = EvalCase.load("evals/cases/hfix-refactor-noop-guard.yaml")
    runner = EvalRunner()

    result = await runner.run(
        case,
        EvalRunInput(
            telemetry_events=[
                {"kind": "tool_call_completed"},
                {"kind": "turn_completed"},
                {"kind": "no_tests_collected"},
            ],
        ),
    )

    assert not result.passed
    assert result.must_not_have_present == ["no_tests_collected"]


def test_load_cases_skips_schema_file():
    cases = load_cases("evals/cases")

    assert {case.id for case in cases} >= {
        "hfix-refactor-noop-guard",
        "p1-headless-ndjson",
        "p1-compaction-path-a",
        "p1-simple-edit",
        "p1-tool-output-shape",
        "p1-usage-reporting",
        "p1-write-read-round-trip",
    }
    assert "example-case" not in {case.id for case in cases}


def test_select_stratified_sample_is_source_balanced():
    cases = [
        EvalCase.load("evals/cases/hfix-refactor-noop-guard.yaml"),
        EvalCase.load("evals/cases/p1-compaction-path-a.yaml"),
    ]

    sample = select_stratified_sample(cases, 1)

    assert len(sample) == 1


@pytest.mark.asyncio
async def test_eval_runner_live_command_parses_ndjson(tmp_path):
    script = tmp_path / "fake_autocode.py"
    script.write_text(
        """
import json
import sys

prompt = sys.argv[1]
events = [
    {"type": "turn_started", "message": prompt},
    {"type": "compaction_event"},
    {"type": "item_delta", "delta": "fixed"},
    {"type": "turn_completed"},
]
for event in events:
    print(json.dumps(event))
""",
        encoding="utf-8",
    )
    case = EvalCase.load("evals/cases/p1-compaction-path-a.yaml")
    runner = EvalRunner(
        agent_command=EvalAgentCommand(
            executable=sys.executable,
            args=(str(script),),
            json_output=True,
            auto_approve=True,
        )
    )

    result = await runner.run_live(case)

    assert result.passed
    assert result.must_have_missing == []


@pytest.mark.asyncio
async def test_eval_runner_live_command_nonzero_adds_error_event(tmp_path):
    script = tmp_path / "fake_autocode_fail.py"
    script.write_text(
        """
import sys

print("not-json")
raise SystemExit(7)
""",
        encoding="utf-8",
    )
    case = EvalCase.from_dict({
        "id": "live-nonzero",
        "name": "Live nonzero",
        "provenance": {"source": "unit", "bug_id": "nonzero", "recorded_at": ""},
        "setup": {"fixture_repo": "", "initial_files": {}},
        "input": {"user_message": "run"},
        "expected_outcomes": {
            "must_have": ["turn_completed"],
            "must_not_have": ["error"],
            "judge_criteria": [],
        },
        "config": {
            "model": "coding",
            "max_turns": 1,
            "timeout_sec": 10,
            "temperature": 0.0,
            "seed": 0,
        },
        "baseline": {
            "correctness_score": 1.0,
            "minimality_score": 1.0,
            "test_quality_score": 1.0,
            "cost_usd_p50": 0.0,
        },
    })
    runner = EvalRunner(
        agent_command=EvalAgentCommand(
            executable=sys.executable,
            args=(str(script),),
            json_output=False,
            auto_approve=False,
        )
    )

    result = await runner.run_live(case)

    assert not result.passed
    assert "error" in result.must_not_have_present


@pytest.mark.asyncio
async def test_eval_runner_live_command_captures_post_run_diff(tmp_path):
    script = tmp_path / "fake_autocode_edit.py"
    script.write_text(
        """
import json
from pathlib import Path

Path("notes.txt").write_text("changed\\n", encoding="utf-8")
print(json.dumps({"type": "turn_completed"}))
""",
        encoding="utf-8",
    )
    case = EvalCase.from_dict({
        "id": "live-diff",
        "name": "Live diff",
        "provenance": {"source": "unit", "bug_id": "diff", "recorded_at": ""},
        "setup": {
            "fixture_repo": "",
            "initial_files": {"notes.txt": "original\n"},
        },
        "input": {"user_message": "edit"},
        "expected_outcomes": {
            "must_have": ["turn_completed"],
            "must_not_have": [],
            "judge_criteria": ["correctness"],
        },
        "config": {
            "model": "coding",
            "max_turns": 1,
            "timeout_sec": 10,
            "temperature": 0.0,
            "seed": 0,
        },
        "baseline": {
            "correctness_score": 1.0,
            "minimality_score": 1.0,
            "test_quality_score": 1.0,
            "cost_usd_p50": 0.0,
        },
    })
    captured: dict[str, str] = {}

    async def judge_provider(prompt: str) -> dict[str, object]:
        captured["prompt"] = prompt
        return {
            "correctness": {
                "score": 1.0,
                "justification": "diff captured",
                "evidence": "notes.txt",
            }
        }

    from evals.judge import LLMJudge

    runner = EvalRunner(
        judge=LLMJudge(provider=judge_provider),
        agent_command=EvalAgentCommand(
            executable=sys.executable,
            args=(str(script),),
            json_output=False,
            auto_approve=False,
        ),
    )

    result = await runner.run_live(case)

    assert result.passed
    assert "-original" in captured["prompt"]
    assert "+changed" in captured["prompt"]


@pytest.mark.asyncio
async def test_eval_runner_live_command_captures_test_command_output(tmp_path):
    script = tmp_path / "fake_autocode_noop.py"
    script.write_text(
        """
import json

print(json.dumps({"type": "turn_completed"}))
""",
        encoding="utf-8",
    )
    test_script = tmp_path / "fake_tests.py"
    test_script.write_text(
        """
print("scenario tests passed")
""",
        encoding="utf-8",
    )
    case = EvalCase.from_dict({
        "id": "live-test-output",
        "name": "Live test output",
        "provenance": {"source": "unit", "bug_id": "test-output", "recorded_at": ""},
        "setup": {"fixture_repo": "", "initial_files": {}},
        "input": {"user_message": "run"},
        "expected_outcomes": {
            "must_have": ["turn_completed"],
            "must_not_have": [],
            "judge_criteria": ["test_quality"],
        },
        "config": {
            "model": "coding",
            "max_turns": 1,
            "timeout_sec": 10,
            "temperature": 0.0,
            "seed": 0,
        },
        "baseline": {
            "correctness_score": 1.0,
            "minimality_score": 1.0,
            "test_quality_score": 1.0,
            "cost_usd_p50": 0.0,
        },
    })
    captured: dict[str, str] = {}

    async def judge_provider(prompt: str) -> dict[str, object]:
        captured["prompt"] = prompt
        return {
            "test_quality": {
                "score": 1.0,
                "justification": "tests captured",
                "evidence": "scenario tests passed",
            }
        }

    from evals.judge import LLMJudge

    runner = EvalRunner(
        judge=LLMJudge(provider=judge_provider),
        agent_command=EvalAgentCommand(
            executable=sys.executable,
            args=(str(script),),
            json_output=False,
            auto_approve=False,
            test_command=(sys.executable, str(test_script)),
        ),
    )

    result = await runner.run_live(case)

    assert result.passed
    assert "scenario tests passed" in captured["prompt"]
