"""Runner for AI verification scenarios.

Modes:
  --agent autocode|codex|claude   run the named agent against the sandboxed scenario
  --validate-fixture              skip agent, grade the pre-agent fixture state only
                                  (confirms scenario is well-formed: green = fixture compiles/tests,
                                   or for dirty scenarios, that it starts in the expected broken state)

Usage:
  uv run python benchmarks/ai_verification/run_scenario.py \\
    --scenario benchmarks/ai_verification/canary_scenarios/01_backend_health_endpoint.json \\
    --validate-fixture

  uv run python benchmarks/ai_verification/run_scenario.py \\
    --scenario benchmarks/ai_verification/canary_scenarios/01_backend_health_endpoint.json \\
    --agent autocode

Artifacts land in: autocode/docs/qa/test-results/ai-verification/<run_id>/
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from benchmarks.ai_verification.grading_env import grading_env
from benchmarks.ai_verification.sandbox_builder import build_sandbox, snapshot_repo, teardown_sandbox
from benchmarks.ai_verification.schema import (
    Check,
    GradingReport,
    CheckResult,
    QA_BASE,
    RunMeta,
    ScenarioSpec,
    Verdict,
    artifact_dir,
    new_run_id,
    sandbox_dir,
)
from benchmarks.ai_verification.run_artifacts import (
    write_tool_calls_jsonl,
    write_turns_json,
    write_trajectory_report,
    write_run_summary,
)
from benchmarks.ai_verification.artifact_grader import (
    grade_artifacts,
    extract_changed_files,
)


@dataclass
class AgentRunEvidence:
    exit_status: int = 0
    tool_calls: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    transcript_lines: list[dict] = field(default_factory=list)
    agent_error: str = ""
    ndjson_raw_lines: list[str] = field(default_factory=list)
    turn_count: int = 0
    turn_summaries: list[dict[str, Any]] = field(default_factory=list)


def run(
    scenario_path: Path,
    agent: str | None = None,
    validate_fixture: bool = False,
    keep_sandbox: bool = False,
    qa_base: Path | None = None,
) -> tuple[str, GradingReport]:
    qa_base = qa_base or QA_BASE
    scenario = ScenarioSpec.load(scenario_path)
    run_id = new_run_id()
    arts = artifact_dir(run_id, qa_base)
    arts.mkdir(parents=True, exist_ok=True)

    sandbox = sandbox_dir(run_id)
    started_at = datetime.now(timezone.utc).isoformat()
    t0 = time.monotonic()

    print(f"[run_scenario] run_id={run_id}")
    print(f"[run_scenario] scenario={scenario.title!r} ({scenario.category.value}, {scenario.difficulty.value})")
    print(f"[run_scenario] mode={'validate-fixture' if validate_fixture else agent}")

    # 1. Save frozen scenario input
    scenario.save(arts / "scenario.json")

    # 2. Build sandbox
    try:
        print(f"[run_scenario] building sandbox at {sandbox}")
        build_sandbox(scenario.repo_seed, sandbox)
    except Exception as exc:
        _write_infra_fail(arts, run_id, scenario, started_at, t0, str(exc))
        raise

    # 3. Snapshot pre-agent repo state
    try:
        snapshot_repo(sandbox, arts / "repo_seed")
    except Exception as exc:
        print(f"[run_scenario] WARN snapshot failed: {exc}")

    evidence = AgentRunEvidence()

    if not validate_fixture and agent:
        print(f"[run_scenario] running agent: {agent}")
        evidence = _run_agent(agent, scenario, sandbox, arts)
    else:
        print("[run_scenario] skipping agent (validate-fixture mode)")
        evidence.transcript_lines = [{"role": "system", "content": "validate-fixture: no agent run"}]

    # 5. Capture diff
    _capture_diff(sandbox, arts / "diff.patch")

    # 5a. Extract structured tool calls from events
    tool_call_records = _extract_tool_call_records(mt_events=None, raw_lines=evidence.ndjson_raw_lines)
    changed_files = extract_changed_files((arts / "diff.patch").read_text())
    diff_text = (arts / "diff.patch").read_text()

    # 5b. Run trajectory grading (if trajectory_assertions exist)
    trajectory_report = None
    if scenario.trajectory_assertions:
        from benchmarks.ai_verification.trajectory_grader import grade_trajectory
        trajectory_report = grade_trajectory(tool_call_records, scenario.trajectory_assertions)
        write_trajectory_report({
            "passed": trajectory_report.passed,
            "results": [{"assertion": r.assertion, "passed": r.passed, "detail": r.detail} for r in trajectory_report.results],
        }, arts / "trajectory_report.json")
    else:
        write_trajectory_report({"passed": True, "results": []}, arts / "trajectory_report.json")

    # 5c. Run artifact grading (if artifact_assertions exist)
    artifact_report = None
    if scenario.artifact_assertions:
        artifact_report = grade_artifacts(
            diff_patch=diff_text,
            changed_files=changed_files,
            sandbox=sandbox if sandbox.is_dir() else None,
            assertions=scenario.artifact_assertions,
        )
        (arts / "artifact_report.json").write_text(
            json.dumps(_assertion_report_payload(artifact_report), indent=2)
        )
    else:
        (arts / "artifact_report.json").write_text(
            json.dumps({"passed": True, "results": []}, indent=2)
        )

    # 5d. Run turn grading and write per-turn artifact
    turn_report = None
    if scenario.turn_assertions:
        from benchmarks.ai_verification.turn_grader import grade_turns
        turn_report = grade_turns(
            turn_count=evidence.turn_count,
            turns=evidence.turn_summaries,
            assertions=scenario.turn_assertions,
        )
        (arts / "turn_report.json").write_text(json.dumps({
            "passed": turn_report.passed,
            "results": [{"assertion": r.assertion, "passed": r.passed, "detail": r.detail} for r in turn_report.results],
        }, indent=2))
    else:
        (arts / "turn_report.json").write_text(json.dumps({"passed": True, "results": []}, indent=2))

    # 5d. Write tool_calls.jsonl
    write_tool_calls_jsonl(tool_call_records, arts / "tool_calls.jsonl")
    write_turns_json(evidence.turn_summaries, arts / "turns.json")

    # 5b-orig. Run NDJSON expected-outcomes grading (if agent ran and expected_outcomes exist)
    ndjson_grader_result = None
    must_have = scenario.expected_outcomes.get("must_have", [])
    must_not_have = scenario.expected_outcomes.get("must_not_have", [])
    if evidence.ndjson_raw_lines and (must_have or must_not_have):
        from benchmarks.ai_verification.ndjson_grader import grade_ndjson
        ndjson_grader_result = grade_ndjson(evidence.ndjson_raw_lines, must_have, must_not_have)
        (arts / "ndjson_grading.json").write_text(json.dumps({
            "passed": ndjson_grader_result.passed,
            "failures": ndjson_grader_result.failures,
            "warnings": ndjson_grader_result.warnings,
        }, indent=2))
        print(f"[run_scenario] NDJSON grading: {'PASS' if ndjson_grader_result.passed else 'FAIL'}")
        for w in ndjson_grader_result.warnings:
            print(f"  {w}")
        if not ndjson_grader_result.passed:
            for f in ndjson_grader_result.failures:
                print(f"  {f}")

    # Hidden tests are injected after the agent run so visible test rewrites
    # cannot mask API regressions or deleted reference assertions.
    _write_hidden_test_files(sandbox, scenario.artifact_assertions)

    # 6. Run deterministic grading checks
    print("[run_scenario] running grading checks...")
    check_results, test_log = _run_checks(scenario, sandbox)
    hidden_results, hidden_log = _run_hidden_checks(scenario, sandbox)
    hidden_checks_failed = any(not result.passed for result in hidden_results)
    check_results.extend(hidden_results)
    if hidden_log:
        test_log = "\n".join(part for part in (test_log, hidden_log) if part)
    (arts / "test_log.txt").write_text(test_log)

    all_passed = all(r.passed for r in check_results)
    infra = None
    if not validate_fixture and agent:
        from benchmarks.ai_verification.infra_classifier import classify_infra
        infra = classify_infra(
            events=_raw_event_dicts(evidence.ndjson_raw_lines),
            error=evidence.agent_error,
            turn_count=evidence.turn_count,
            check_output=test_log,
        )

    infra_blocks_verdict = _infra_blocks_verdict(
        infra=infra,
        evidence=evidence,
        all_passed=all_passed,
        trajectory_report=trajectory_report,
        artifact_report=artifact_report,
        turn_report=turn_report,
        ndjson_grader_result=ndjson_grader_result,
    )

    if infra_blocks_verdict:
        verdict = Verdict.INFRA_FAIL
    elif trajectory_report is not None and not trajectory_report.passed:
        verdict = Verdict.FAIL
    elif artifact_report is not None and not artifact_report.passed:
        verdict = Verdict.FAIL
    elif turn_report is not None and not turn_report.passed:
        verdict = Verdict.FAIL
    elif validate_fixture:
        eff = scenario.grading.expect_fixture_failure
        if eff is False:
            verdict = Verdict.PASS if all_passed else Verdict.FAIL
        else:
            expected_fail = scenario.category.value in ("dirty_cleanup", "repo_init", "migration")
            if expected_fail:
                verdict = Verdict.PASS if not all_passed else Verdict.FAIL
                if verdict == Verdict.FAIL:
                    print(f"[run_scenario] WARN: {scenario.category.value} fixture started CLEAN — scenario may not inject dirt correctly")
            else:
                verdict = Verdict.PASS if all_passed else Verdict.FAIL
    elif ndjson_grader_result is not None and not ndjson_grader_result.passed:
        verdict = Verdict.FAIL
    elif not check_results:
        verdict = Verdict.INFRA_FAIL
    elif hidden_checks_failed:
        verdict = Verdict.FAIL
    elif all_passed:
        verdict = Verdict.PASS
    elif any(r.passed for r in check_results):
        verdict = Verdict.PARTIAL
    else:
        verdict = Verdict.FAIL

    primary_verdict = _primary_non_infra_verdict(
        trajectory_report=trajectory_report,
        artifact_report=artifact_report,
        turn_report=turn_report,
        validate_fixture=validate_fixture,
        scenario=scenario,
        ndjson_grader_result=ndjson_grader_result,
        check_results=check_results,
        hidden_checks_failed=hidden_checks_failed,
        all_passed=all_passed,
    )
    agent_fail_signals = _agent_fail_signals(
        evidence=evidence,
        all_passed=all_passed,
        check_results=check_results,
        trajectory_report=trajectory_report,
        artifact_report=artifact_report,
        turn_report=turn_report,
        ndjson_grader_result=ndjson_grader_result,
        hidden_checks_failed=hidden_checks_failed,
    )

    report = GradingReport(
        verdict=verdict,
        check_results=check_results,
        ai_review_enabled=False,
        trajectory_passed=trajectory_report.passed if trajectory_report else None,
        artifact_passed=artifact_report.passed if artifact_report else None,
        turn_passed=turn_report.passed if turn_report else None,
        artifact_results=_assertion_results(artifact_report) if artifact_report else [],
    )
    report.save(arts / "grading_report.json")

    # 7b. Write run_summary.json
    tool_histogram: dict[str, int] = {}
    for tc in tool_call_records:
        name = tc.get("tool_name", "unknown")
        tool_histogram[name] = tool_histogram.get(name, 0) + 1

    write_run_summary({
        "run_id": run_id,
        "scenario_id": scenario.scenario_id,
        "scenario_title": scenario.title,
        "verdict": verdict.value,
        "primary_verdict": primary_verdict.value,
        "turn_count": evidence.turn_count,
        "tool_histogram": tool_histogram,
        "required_tools_satisfied": trajectory_report.passed if trajectory_report else not scenario.trajectory_assertions,
        "trajectory_satisfied": trajectory_report.passed if trajectory_report else not scenario.trajectory_assertions,
        "artifact_assertions_satisfied": artifact_report.passed if artifact_report else not scenario.artifact_assertions,
        "turn_assertions_satisfied": turn_report.passed if turn_report else not scenario.turn_assertions,
        "deterministic_checks_satisfied": all_passed,
        "artifact_complete": True,
        "changed_files": changed_files,
        "infra_fail_reason": infra.reason if infra_blocks_verdict and infra else "",
        "infra_detected": bool(infra and infra.is_infra_fail),
        "infra_signals": list(infra.signals) if infra else [],
        "infra_detected_reason": infra.reason if infra else "",
        "infra_blocks_verdict": infra_blocks_verdict,
        "agent_fail_signals": agent_fail_signals,
    }, arts / "run_summary.json")

    # 7. Save transcript
    (arts / "agent_transcript.jsonl").write_text(
        "\n".join(json.dumps(t) for t in evidence.transcript_lines)
    )

    # 8. Save meta
    finished_at = datetime.now(timezone.utc).isoformat()
    wall_time_s = time.monotonic() - t0
    meta = RunMeta(
        run_id=run_id,
        scenario_id=scenario.scenario_id,
        agent=agent or "validate-fixture",
        status=verdict.value,
        started_at=started_at,
        finished_at=finished_at,
        wall_time_s=round(wall_time_s, 2),
        exit_status=evidence.exit_status,
        tool_calls=evidence.tool_calls,
        tokens_in=evidence.tokens_in,
        tokens_out=evidence.tokens_out,
        error=evidence.agent_error,
        infra_fail_reason=infra.reason if infra_blocks_verdict and infra else "",
    )
    meta.save(arts / "meta.json")

    # 9. Cleanup sandbox
    if not keep_sandbox:
        teardown_sandbox(sandbox)

    print(f"[run_scenario] verdict={verdict.value}  wall_time={wall_time_s:.1f}s")
    print(f"[run_scenario] artifacts at {arts}")
    return run_id, report


def _run_checks(
    scenario: ScenarioSpec, sandbox: Path
) -> tuple[list[CheckResult], str]:
    from benchmarks.ai_verification.grade_run import _default_command

    results: list[CheckResult] = []
    log_parts: list[str] = []
    env = grading_env()

    for check in scenario.grading.checks:
        cmd = scenario.grading.check_commands.get(check.value, "")
        if not cmd:
            cmd = _default_command(check, scenario)

        log_parts.append(f"=== {check.value}: {cmd} ===")
        try:
            proc = subprocess.run(
                cmd, shell=True, cwd=sandbox, capture_output=True, text=True, timeout=120,
                env=env,
            )
            output = proc.stdout + proc.stderr
            passed = proc.returncode == 0
            exit_code = proc.returncode
        except subprocess.TimeoutExpired:
            output = "TIMEOUT after 120s"
            passed = False
            exit_code = 124

        if _pytest_collected_zero_tests(output):
            passed = False
            output = output.rstrip() + "\nHARNESS_CLASSIFICATION: zero_tests_collected\n"

        log_parts.append(output)
        results.append(
            CheckResult(
                check=check,
                passed=passed,
                command=cmd,
                output=output,
                exit_code=exit_code,
            )
        )

    return results, "\n".join(log_parts)


def _write_hidden_test_files(sandbox: Path, assertions: dict[str, Any] | None) -> None:
    hidden_files = (assertions or {}).get("hidden_test_files", {})
    if not isinstance(hidden_files, dict) or not hidden_files:
        return
    hidden_root = sandbox / ".autocode_hidden_tests"
    hidden_root.mkdir(parents=True, exist_ok=True)
    for rel_path, content in hidden_files.items():
        target = hidden_root / str(rel_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(str(content), encoding="utf-8")


def _run_hidden_checks(
    scenario: ScenarioSpec, sandbox: Path
) -> tuple[list[CheckResult], str]:
    assertions = scenario.artifact_assertions or {}
    hidden_files = assertions.get("hidden_test_files", {})
    if not isinstance(hidden_files, dict) or not hidden_files:
        return [], ""

    cmd = str(
        assertions.get("hidden_test_command")
        or "python -m pytest .autocode_hidden_tests -v"
    )
    env = grading_env()
    log_parts = [f"=== hidden-tests: {cmd} ==="]
    try:
        proc = subprocess.run(
            cmd,
            shell=True,
            cwd=sandbox,
            capture_output=True,
            text=True,
            timeout=120,
            env=env,
        )
        output = proc.stdout + proc.stderr
        passed = proc.returncode == 0
        exit_code = proc.returncode
    except subprocess.TimeoutExpired:
        output = "TIMEOUT after 120s"
        passed = False
        exit_code = 124

    if _pytest_collected_zero_tests(output):
        passed = False
        output = output.rstrip() + "\nHARNESS_CLASSIFICATION: zero_tests_collected\n"

    log_parts.append(output)
    return [
        CheckResult(
            check=Check.RUN_TESTS,
            passed=passed,
            command=cmd,
            output=output,
            exit_code=exit_code,
        )
    ], "\n".join(log_parts)


def _pytest_collected_zero_tests(output: str) -> bool:
    normalized = output.lower()
    return "collected 0 items" in normalized or "no tests ran" in normalized


def _assertion_results(report: Any) -> list[dict[str, Any]]:
    return [
        {
            "assertion": result.assertion,
            "passed": result.passed,
            "detail": result.detail,
        }
        for result in getattr(report, "results", [])
    ]


def _assertion_report_payload(report: Any) -> dict[str, Any]:
    return {
        "passed": bool(getattr(report, "passed", False)),
        "results": _assertion_results(report),
    }


def _capture_diff(sandbox: Path, out_path: Path) -> None:
    try:
        proc = subprocess.run(
            "git diff HEAD",
            shell=True,
            cwd=sandbox,
            capture_output=True,
            text=True,
            timeout=30,
        )
        out_path.write_text(proc.stdout or "(no changes from seed commit)")
    except Exception as exc:
        out_path.write_text(f"diff capture failed: {exc}")


def _extract_tool_call_records(mt_events, raw_lines: list[str]) -> list[dict]:
    records = []
    source = raw_lines or []
    for line in source:
        line = line.strip()
        if not line:
            continue
        try:
            raw = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        event_type = raw.get("type", "")
        if event_type in ("tool_call_completed", "tool_call_failed"):
            records.append(raw)
    return records


def _raw_event_dicts(raw_lines: list[str]) -> list[dict[str, Any]]:
    events = []
    for line in raw_lines or []:
        try:
            raw = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(raw, dict):
            events.append(raw)
    return events


def _infra_blocks_verdict(
    *,
    infra: Any,
    evidence: AgentRunEvidence,
    all_passed: bool,
    trajectory_report: Any,
    artifact_report: Any,
    turn_report: Any,
    ndjson_grader_result: Any,
) -> bool:
    if infra is None or not infra.is_infra_fail:
        return False
    if "rate_limit_detected" not in getattr(infra, "signals", []):
        return True
    if evidence.exit_status != 0 or evidence.turn_count <= 0:
        return True
    if not all_passed:
        return True
    if trajectory_report is not None and not trajectory_report.passed:
        return True
    if artifact_report is not None and not artifact_report.passed:
        return True
    if turn_report is not None and not turn_report.passed:
        return True
    if ndjson_grader_result is not None and not ndjson_grader_result.passed:
        return True
    return False


def _primary_non_infra_verdict(
    *,
    trajectory_report: Any,
    artifact_report: Any,
    turn_report: Any,
    validate_fixture: bool,
    scenario: ScenarioSpec,
    ndjson_grader_result: Any,
    check_results: list[CheckResult],
    hidden_checks_failed: bool,
    all_passed: bool,
) -> Verdict:
    """Return the behavior verdict before infra masking is applied."""

    if trajectory_report is not None and not trajectory_report.passed:
        return Verdict.FAIL
    if artifact_report is not None and not artifact_report.passed:
        return Verdict.FAIL
    if turn_report is not None and not turn_report.passed:
        return Verdict.FAIL
    if validate_fixture:
        eff = scenario.grading.expect_fixture_failure
        if eff is False:
            return Verdict.PASS if all_passed else Verdict.FAIL
        expected_fail = scenario.category.value in ("dirty_cleanup", "repo_init", "migration")
        return Verdict.PASS if (not all_passed if expected_fail else all_passed) else Verdict.FAIL
    if ndjson_grader_result is not None and not ndjson_grader_result.passed:
        return Verdict.FAIL
    if not check_results:
        return Verdict.INFRA_FAIL
    if hidden_checks_failed:
        return Verdict.FAIL
    if all_passed:
        return Verdict.PASS
    if any(r.passed for r in check_results):
        return Verdict.PARTIAL
    return Verdict.FAIL


def _agent_fail_signals(
    *,
    evidence: AgentRunEvidence,
    all_passed: bool,
    check_results: list[CheckResult],
    trajectory_report: Any,
    artifact_report: Any,
    turn_report: Any,
    ndjson_grader_result: Any,
    hidden_checks_failed: bool,
) -> list[str]:
    signals: list[str] = []
    if evidence.exit_status != 0:
        signals.append("agent_exit_nonzero")
    if not check_results:
        signals.append("no_check_results")
    elif not all_passed:
        signals.append("deterministic_checks_failed")
    if trajectory_report is not None and not trajectory_report.passed:
        signals.append("trajectory_assertions_failed")
    if artifact_report is not None and not artifact_report.passed:
        signals.append("artifact_assertions_failed")
    if turn_report is not None and not turn_report.passed:
        signals.append("turn_assertions_failed")
    if ndjson_grader_result is not None and not ndjson_grader_result.passed:
        signals.append("ndjson_assertions_failed")
    if hidden_checks_failed:
        signals.append("hidden_checks_failed")
    return signals


def _normalize_agent_result(result: Any) -> AgentRunEvidence:
    if isinstance(result, AgentRunEvidence):
        return result
    if isinstance(result, tuple):
        values = list(result)
        if len(values) < 7:
            raise ValueError(f"agent result tuple too short: {len(values)}")
        turn_count = values[7] if len(values) >= 8 else (1 if values[6] else 0)
        turn_summaries = values[8] if len(values) >= 9 else []
        return AgentRunEvidence(
            exit_status=values[0],
            tool_calls=values[1],
            tokens_in=values[2],
            tokens_out=values[3],
            transcript_lines=values[4],
            agent_error=values[5],
            ndjson_raw_lines=values[6],
            turn_count=turn_count,
            turn_summaries=turn_summaries,
        )
    raise TypeError(f"unsupported agent result: {type(result).__name__}")


def _run_agent(
    agent: str,
    scenario: ScenarioSpec,
    sandbox: Path,
    arts: Path,
) -> AgentRunEvidence:
    """Run agent and normalize adapter-specific results into harness evidence."""
    transcript_path = arts / "agent_transcript.jsonl"
    if agent == "autocode":
        return _normalize_agent_result(_run_autocode(scenario, sandbox, transcript_path))
    elif agent in ("codex", "claude"):
        return AgentRunEvidence(exit_status=1, agent_error=f"agent '{agent}' adapter not yet implemented")
    else:
        return AgentRunEvidence(exit_status=1, agent_error=f"unknown agent: {agent!r}")


def _run_autocode(
    scenario: ScenarioSpec, sandbox: Path, transcript_path: Path
) -> AgentRunEvidence:
    """Run autocode multi-turn (subprocess per turn, sandbox cwd) against the scenario."""
    from benchmarks.ai_verification.multiturn_runner import run_multiturn

    mt = run_multiturn(scenario, sandbox)

    for note in mt.turn_outputs:
        print(f"[run_scenario]   {note}")
    print(f"[run_scenario] turns_used={mt.turns}  grading_passed={mt.grading_passed}")

    raw_lines = []
    for event in mt.events:
        dump = event.model_dump() if hasattr(event, "model_dump") else str(event)
        raw_lines.append(json.dumps(dump))

    transcript_lines = [json.loads(line) for line in raw_lines] if raw_lines else [
        {"role": "system", "content": "no events captured"}
    ]
    transcript_path.write_text("\n".join(json.dumps(t) for t in transcript_lines))

    return AgentRunEvidence(
        exit_status=mt.exit_code,
        tool_calls=mt.tool_calls,
        tokens_in=mt.tokens_in,
        tokens_out=mt.tokens_out,
        transcript_lines=transcript_lines,
        agent_error=mt.error,
        ndjson_raw_lines=raw_lines,
        turn_count=mt.turns,
        turn_summaries=mt.turn_summaries,
    )


def _write_infra_fail(
    arts: Path, run_id: str, scenario: ScenarioSpec,
    started_at: str, t0: float, error: str
) -> None:
    report = GradingReport(
        verdict=Verdict.INFRA_FAIL,
        check_results=[],
        ai_review_enabled=False,
        ai_reasoning=error,
    )
    report.save(arts / "grading_report.json")
    meta = RunMeta(
        run_id=run_id,
        scenario_id=scenario.scenario_id,
        agent="n/a",
        status=Verdict.INFRA_FAIL.value,
        started_at=started_at,
        finished_at=datetime.now(timezone.utc).isoformat(),
        wall_time_s=round(time.monotonic() - t0, 2),
        exit_status=1,
        error=error,
    )
    meta.save(arts / "meta.json")
    (arts / "test_log.txt").write_text(f"INFRA FAIL: {error}")
    (arts / "diff.patch").write_text("")
    (arts / "agent_transcript.jsonl").write_text("")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run an AI verification scenario")
    parser.add_argument("--scenario", type=Path, required=True)
    parser.add_argument("--agent", choices=["autocode", "codex", "claude"])
    parser.add_argument("--validate-fixture", action="store_true")
    parser.add_argument("--keep-sandbox", action="store_true")
    parser.add_argument("--base", type=Path, default=None, help="Override QA base path")
    args = parser.parse_args()

    if not args.validate_fixture and not args.agent:
        parser.error("Specify --agent or --validate-fixture")

    run(
        scenario_path=args.scenario,
        agent=args.agent,
        validate_fixture=args.validate_fixture,
        keep_sandbox=args.keep_sandbox,
        qa_base=args.base,
    )


if __name__ == "__main__":
    main()
