"""Supervised runner for live AI verification scenarios.

This wrapper adds an outer timeout around ``run_scenario`` and converts a
timed-out partial run directory into auditable ``INFRA_FAIL`` artifacts.
It is intentionally separate from ``run_scenario`` so normal harness verdicts
are not hidden or retried by the supervisor.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import selectors
import signal
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from benchmarks.ai_verification.run_artifacts import (
    write_run_summary,
    write_tool_calls_jsonl,
    write_trajectory_report,
    write_turns_json,
)
from benchmarks.ai_verification.schema import (
    GradingReport,
    QA_BASE,
    RunMeta,
    ScenarioSpec,
    Verdict,
    artifact_dir,
    new_run_id,
)


RUN_ID_RE = re.compile(r"^\[run_scenario\]\s+run_id=(?P<run_id>\S+)\s*$")
DEFAULT_RETRY_SCHEDULE_SECONDS = [
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


@dataclass
class SupervisedRunReport:
    scenario: str
    agent: str
    command: list[str]
    timed_out: bool
    exit_code: int
    final_run_id: str
    final_run_dir: str
    final_verdict: str
    reason: str
    output_log: str
    report_dir: str

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(asdict(self), indent=2, default=str) + "\n")


@dataclass
class BatchSupervisedReport:
    scenario_input: str
    tag: str | None
    agent: str
    scenario_count: int
    verdict_counts: dict[str, int]
    runs: list[dict[str, object]]
    batch_dir: str
    manifest_path: str
    exit_code: int

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(asdict(self), indent=2, default=str) + "\n")


def parse_retry_schedule(value: str) -> list[int]:
    """Parse a comma-separated retry schedule like ``5s,30s,1m,2h``."""

    delays: list[int] = []
    for raw_part in value.split(","):
        part = raw_part.strip().lower()
        if not part:
            continue
        unit = part[-1]
        number_text = part[:-1] if unit in {"s", "m", "h"} else part
        try:
            amount = int(number_text)
        except ValueError as exc:
            raise argparse.ArgumentTypeError(
                f"invalid retry delay {raw_part!r}",
            ) from exc
        if amount < 0:
            raise argparse.ArgumentTypeError(
                f"retry delay must be non-negative: {raw_part!r}",
            )
        multiplier = {"s": 1, "m": 60, "h": 3600}.get(unit, 1)
        delays.append(amount * multiplier)
    return delays


def discover_scenarios(scenario_input: Path, *, tag: str | None = None) -> list[Path]:
    """Resolve a scenario file or directory into a stable ordered scenario list."""

    scenario_input = Path(scenario_input)
    if scenario_input.is_file():
        candidates = [scenario_input]
    elif scenario_input.is_dir():
        candidates = sorted(
            path
            for suffix in ("*.yaml", "*.yml", "*.json")
            for path in scenario_input.rglob(suffix)
            if path.is_file()
        )
    else:
        raise FileNotFoundError(f"scenario input not found: {scenario_input}")

    if not tag:
        return candidates
    return [path for path in candidates if _scenario_matches_tag(path, tag)]


def run_batch_supervised(
    *,
    scenario_input: Path,
    tag: str | None,
    agent: str,
    qa_base: Path,
    report_base: Path,
    timeout_seconds: int,
    retry_schedule_seconds: list[int] | None = None,
) -> BatchSupervisedReport:
    """Run a supervised batch and continue through per-scenario failures."""

    scenario_paths = discover_scenarios(scenario_input, tag=tag)
    report_base = Path(report_base)
    batch_dir = report_base / f"{_stamp()}-batch-supervised"
    batch_dir.mkdir(parents=True, exist_ok=True)

    runs: list[dict[str, object]] = []
    verdict_counts: dict[str, int] = {}
    for scenario_path in scenario_paths:
        command = _default_command(scenario_path, agent, Path(qa_base))
        report = run_supervised_with_retries(
            command=command,
            scenario_path=scenario_path,
            agent=agent,
            qa_base=Path(qa_base),
            report_base=report_base,
            timeout_seconds=timeout_seconds,
            retry_schedule_seconds=retry_schedule_seconds,
        )
        verdict_counts[report.final_verdict] = verdict_counts.get(report.final_verdict, 0) + 1
        runs.append(
            {
                "scenario": str(scenario_path),
                "scenario_name": scenario_path.name,
                "scenario_hash": _sha256_file(scenario_path),
                "run_id": report.final_run_id,
                "run_dir": report.final_run_dir,
                "report_dir": report.report_dir,
                "verdict": report.final_verdict,
                "timed_out": report.timed_out,
                "exit_code": report.exit_code,
                "reason": report.reason,
            }
        )

    exit_code = 0 if scenario_paths and verdict_counts.get(Verdict.PASS.value, 0) == len(scenario_paths) else 1
    manifest_path = batch_dir / "batch_manifest.json"
    batch = BatchSupervisedReport(
        scenario_input=str(scenario_input),
        tag=tag,
        agent=agent,
        scenario_count=len(scenario_paths),
        verdict_counts=verdict_counts,
        runs=runs,
        batch_dir=str(batch_dir),
        manifest_path=str(manifest_path),
        exit_code=exit_code,
    )
    manifest_path.write_text(
        json.dumps(_batch_manifest_payload(batch, scenario_paths), indent=2, default=str) + "\n",
    )
    batch.save(batch_dir / "batch_report.json")
    (batch_dir / "batch_report.md").write_text(_batch_report_markdown(batch))
    return batch


def run_supervised(
    *,
    command: list[str],
    scenario_path: Path,
    agent: str,
    qa_base: Path,
    report_base: Path,
    timeout_seconds: int,
) -> SupervisedRunReport:
    """Run a scenario command with an outer timeout and complete timeout artifacts."""

    scenario_path = Path(scenario_path)
    qa_base = Path(qa_base)
    report_base = Path(report_base)
    report_dir = report_base / f"{_stamp()}-{scenario_path.stem}-supervised"
    report_dir.mkdir(parents=True, exist_ok=True)
    output_log = report_dir / "supervisor_output.log"

    lines: list[str] = []
    run_id = ""
    timed_out = False
    exit_code = 0
    started = time.monotonic()

    proc = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        start_new_session=True,
    )

    assert proc.stdout is not None
    selector = selectors.DefaultSelector()
    selector.register(proc.stdout, selectors.EVENT_READ)

    try:
        while True:
            elapsed = time.monotonic() - started
            if elapsed >= timeout_seconds and proc.poll() is None:
                timed_out = True
                exit_code = 124
                _terminate_process_group(proc)
                break

            if proc.poll() is not None:
                _drain_available(selector, lines, output_log)
                exit_code = proc.returncode
                break

            timeout = min(0.2, max(timeout_seconds - elapsed, 0.0))
            for key, _ in selector.select(timeout=timeout):
                line = key.fileobj.readline()
                if not line:
                    continue
                _record_line(line, lines, output_log)
                run_id = _extract_run_id(line) or run_id
    finally:
        try:
            selector.unregister(proc.stdout)
        except Exception:
            pass
        proc.stdout.close()

    if not run_id:
        run_id = _extract_run_id("\n".join(lines))

    reason = ""
    if timed_out:
        reason = f"supervisor timeout after {timeout_seconds}s"
        if not run_id:
            run_id = f"{new_run_id()}-supervised-timeout"
        run_dir = artifact_dir(run_id, qa_base)
        complete_infra_fail_artifacts(
            run_dir=run_dir,
            scenario_path=scenario_path,
            agent=agent,
            reason=reason,
            exit_code=exit_code,
            output="\n".join(lines),
        )
        final_verdict = Verdict.INFRA_FAIL.value
    else:
        run_dir = artifact_dir(run_id, qa_base) if run_id else qa_base
        final_verdict = _read_final_verdict(run_dir)
        if final_verdict == "UNKNOWN":
            reason = f"child exited {exit_code} without a readable grading verdict"
            if not run_id:
                run_id = f"{new_run_id()}-supervised-missing-verdict"
                run_dir = artifact_dir(run_id, qa_base)
            complete_infra_fail_artifacts(
                run_dir=run_dir,
                scenario_path=scenario_path,
                agent=agent,
                reason=reason,
                exit_code=exit_code,
                output="\n".join(lines),
            )
            final_verdict = Verdict.INFRA_FAIL.value
        elif exit_code != 0:
            reason = f"child exited {exit_code}; preserved child verdict {final_verdict}"
        else:
            reason = f"child completed with verdict {final_verdict}"

    report = SupervisedRunReport(
        scenario=str(scenario_path),
        agent=agent,
        command=command,
        timed_out=timed_out,
        exit_code=exit_code,
        final_run_id=run_id,
        final_run_dir=str(run_dir),
        final_verdict=final_verdict,
        reason=reason,
        output_log=str(output_log),
        report_dir=str(report_dir),
    )
    report.save(report_dir / "supervisor_report.json")
    (report_dir / "supervisor_report.md").write_text(_report_markdown(report))
    return report


def run_supervised_with_retries(
    *,
    command: list[str],
    scenario_path: Path,
    agent: str,
    qa_base: Path,
    report_base: Path,
    timeout_seconds: int,
    retry_schedule_seconds: list[int] | None = None,
) -> SupervisedRunReport:
    """Run a supervised scenario with default long transient-infra retries."""

    schedule = (
        list(DEFAULT_RETRY_SCHEDULE_SECONDS)
        if retry_schedule_seconds is None
        else list(retry_schedule_seconds)
    )
    scenario_path = Path(scenario_path)
    report_base = Path(report_base)
    retry_dir = report_base / f"{_stamp()}-{scenario_path.stem}-retry-supervised"
    retry_dir.mkdir(parents=True, exist_ok=True)

    attempts: list[dict[str, object]] = []
    final_report: SupervisedRunReport | None = None
    for attempt_index in range(len(schedule) + 1):
        report = run_supervised(
            command=command,
            scenario_path=scenario_path,
            agent=agent,
            qa_base=qa_base,
            report_base=report_base,
            timeout_seconds=timeout_seconds,
        )
        final_report = report
        should_retry = _should_retry_supervised_report(report)
        next_delay_s = (
            schedule[attempt_index]
            if should_retry and attempt_index < len(schedule)
            else 0
        )
        attempts.append(
            {
                "attempt": attempt_index + 1,
                "run_id": report.final_run_id,
                "run_dir": report.final_run_dir,
                "verdict": report.final_verdict,
                "reason": report.reason,
                "timed_out": report.timed_out,
                "exit_code": report.exit_code,
                "report_dir": report.report_dir,
                "next_delay_s": next_delay_s,
            }
        )
        _write_retry_report(
            retry_dir=retry_dir,
            scenario_path=scenario_path,
            agent=agent,
            command=command,
            timeout_seconds=timeout_seconds,
            schedule=schedule,
            attempts=attempts,
            final_report=report,
        )
        if next_delay_s <= 0:
            break
        time.sleep(next_delay_s)

    assert final_report is not None
    final_report.report_dir = str(retry_dir)
    final_report.output_log = str(retry_dir / "retry_report.json")
    final_report.save(retry_dir / "supervisor_report.json")
    (retry_dir / "supervisor_report.md").write_text(_report_markdown(final_report))
    return final_report


def complete_infra_fail_artifacts(
    *,
    run_dir: Path,
    scenario_path: Path,
    agent: str,
    reason: str,
    exit_code: int,
    output: str,
) -> None:
    """Complete a partial run directory as a deterministic INFRA_FAIL."""

    run_dir.mkdir(parents=True, exist_ok=True)
    scenario = ScenarioSpec.load(scenario_path)
    run_id = run_dir.name
    started_at = datetime.now(timezone.utc).isoformat()
    finished_at = datetime.now(timezone.utc).isoformat()

    if not (run_dir / "scenario.json").exists():
        scenario.save(run_dir / "scenario.json")

    report = GradingReport(
        verdict=Verdict.INFRA_FAIL,
        check_results=[],
        ai_review_enabled=False,
        ai_reasoning=reason,
        trajectory_passed=False if scenario.trajectory_assertions else None,
        artifact_passed=False if scenario.artifact_assertions else None,
        turn_passed=False if scenario.turn_assertions else None,
    )
    report.save(run_dir / "grading_report.json")

    meta = RunMeta(
        run_id=run_id,
        scenario_id=scenario.scenario_id,
        agent=agent,
        status=Verdict.INFRA_FAIL.value,
        started_at=started_at,
        finished_at=finished_at,
        wall_time_s=0.0,
        exit_status=exit_code,
        error=output[-4000:],
        infra_fail_reason=reason,
    )
    meta.save(run_dir / "meta.json")

    (run_dir / "test_log.txt").write_text(f"INFRA_FAIL: {reason}\n\n{output}")
    (run_dir / "agent_transcript.jsonl").touch()
    if not (run_dir / "diff.patch").exists():
        (run_dir / "diff.patch").write_text("diff unavailable: run timed out before diff capture\n")
    write_tool_calls_jsonl([], run_dir / "tool_calls.jsonl")
    write_turns_json([], run_dir / "turns.json")

    trajectory_satisfied: bool | None = None
    if scenario.trajectory_assertions:
        from benchmarks.ai_verification.trajectory_grader import grade_trajectory

        trajectory_report = grade_trajectory([], scenario.trajectory_assertions)
        trajectory_satisfied = trajectory_report.passed
        write_trajectory_report(
            {
                "passed": trajectory_report.passed,
                "results": [
                    {"assertion": r.assertion, "passed": r.passed, "detail": r.detail}
                    for r in trajectory_report.results
                ],
                "infra_fail_reason": reason,
            },
            run_dir / "trajectory_report.json",
        )
    else:
        trajectory_satisfied = True
        write_trajectory_report(
            {"passed": True, "results": [], "infra_fail_reason": reason},
            run_dir / "trajectory_report.json",
        )

    turn_satisfied: bool | None = None
    if scenario.turn_assertions:
        from benchmarks.ai_verification.turn_grader import grade_turns

        turn_report = grade_turns(turn_count=0, turns=[], assertions=scenario.turn_assertions)
        turn_satisfied = turn_report.passed
        (run_dir / "turn_report.json").write_text(
            json.dumps(
                {
                    "passed": turn_report.passed,
                    "results": [
                        {"assertion": r.assertion, "passed": r.passed, "detail": r.detail}
                        for r in turn_report.results
                    ],
                    "infra_fail_reason": reason,
                },
                indent=2,
                default=str,
            )
            + "\n"
        )
    else:
        turn_satisfied = True
        (run_dir / "turn_report.json").write_text(
            json.dumps(
                {"passed": True, "results": [], "infra_fail_reason": reason},
                indent=2,
                default=str,
            )
            + "\n"
        )

    (run_dir / "artifact_report.json").write_text(
        json.dumps(
            {
                "passed": False if scenario.artifact_assertions else True,
                "results": [],
                "infra_fail_reason": reason,
            },
            indent=2,
            default=str,
        )
        + "\n"
    )

    write_run_summary(
        {
            "run_id": run_id,
            "scenario_id": scenario.scenario_id,
            "scenario_title": scenario.title,
            "verdict": Verdict.INFRA_FAIL.value,
            "primary_verdict": Verdict.INFRA_FAIL.value,
            "turn_count": 0,
            "tool_histogram": {},
            "required_tools_satisfied": (
                trajectory_satisfied if trajectory_satisfied is not None else not scenario.trajectory_assertions
            ),
            "trajectory_satisfied": (
                trajectory_satisfied if trajectory_satisfied is not None else not scenario.trajectory_assertions
            ),
            "artifact_assertions_satisfied": False if scenario.artifact_assertions else True,
            "turn_assertions_satisfied": turn_satisfied if turn_satisfied is not None else not scenario.turn_assertions,
            "deterministic_checks_satisfied": False,
            "artifact_complete": True,
            "changed_files": [],
            "infra_fail_reason": reason,
            "infra_detected": True,
            "infra_signals": ["supervisor_timeout" if "timeout" in reason.lower() else "supervisor_infra_fail"],
            "infra_detected_reason": reason,
            "infra_blocks_verdict": True,
            "agent_fail_signals": ["no_check_results"],
        },
        run_dir / "run_summary.json",
    )


def _record_line(line: str, lines: list[str], output_log: Path) -> None:
    lines.append(line.rstrip("\n"))
    with output_log.open("a", encoding="utf-8") as fh:
        fh.write(line)


def _drain_available(
    selector: selectors.BaseSelector,
    lines: list[str],
    output_log: Path,
) -> None:
    while True:
        ready = selector.select(timeout=0)
        if not ready:
            return
        for key, _ in ready:
            line = key.fileobj.readline()
            if not line:
                return
            _record_line(line, lines, output_log)


def _terminate_process_group(proc: subprocess.Popen[str]) -> None:
    try:
        os.killpg(proc.pid, signal.SIGTERM)
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.wait(timeout=5)
    except ProcessLookupError:
        pass


def _extract_run_id(output: str) -> str:
    for line in output.splitlines():
        match = RUN_ID_RE.match(line.strip())
        if match:
            return match.group("run_id")
    return ""


def _read_final_verdict(run_dir: Path) -> str:
    for name in ("run_summary.json", "grading_report.json", "meta.json"):
        path = run_dir / name
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        verdict = data.get("verdict") or data.get("status")
        if verdict:
            return str(verdict)
    return "UNKNOWN"


def _should_retry_supervised_report(report: SupervisedRunReport) -> bool:
    return report.final_verdict == Verdict.INFRA_FAIL.value


def _scenario_matches_tag(path: Path, tag: str) -> bool:
    wanted = _normalize_tag(tag)
    if not wanted:
        return True

    values = [path.stem, path.name]
    try:
        scenario = ScenarioSpec.load(path)
    except Exception:
        scenario = None
    if scenario is not None:
        values.extend(
            [
                scenario.title,
                scenario.description,
                scenario.category.value,
                scenario.difficulty.value,
                scenario.target_stack.language,
                scenario.target_stack.framework,
            ]
        )
        values.extend(scenario.task_spec.followup_prompts and ["multiturn", "multi-turn"] or [])

    return any(wanted in _normalize_tag(value) for value in values if value)


def _normalize_tag(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_sha() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception:
        return "unknown"
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def _batch_manifest_payload(
    batch: BatchSupervisedReport,
    scenario_paths: list[Path],
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "git_sha": _git_sha(),
        "environment": {
            "python_version": platform.python_version(),
            "platform": platform.platform(),
        },
        "scenario_input": batch.scenario_input,
        "tag": batch.tag,
        "agent": batch.agent,
        "scenario_count": batch.scenario_count,
        "scenarios": [
            {
                "path": str(path),
                "name": path.name,
                "sha256": _sha256_file(path),
            }
            for path in scenario_paths
        ],
        "runs": batch.runs,
        "verdict_counts": batch.verdict_counts,
        "exit_code": batch.exit_code,
    }


def _write_retry_report(
    *,
    retry_dir: Path,
    scenario_path: Path,
    agent: str,
    command: list[str],
    timeout_seconds: int,
    schedule: list[int],
    attempts: list[dict[str, object]],
    final_report: SupervisedRunReport,
) -> None:
    retry_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "scenario": str(scenario_path),
        "agent": agent,
        "command": command,
        "timeout_seconds": timeout_seconds,
        "retry_schedule_seconds": schedule,
        "attempt_count": len(attempts),
        "attempts": attempts,
        "final_run_id": final_report.final_run_id,
        "final_run_dir": final_report.final_run_dir,
        "final_verdict": final_report.final_verdict,
        "final_reason": final_report.reason,
    }
    (retry_dir / "retry_report.json").write_text(
        json.dumps(payload, indent=2, default=str) + "\n",
    )


def _report_markdown(report: SupervisedRunReport) -> str:
    return (
        f"# Supervised Scenario Run\n\n"
        f"- Scenario: `{report.scenario}`\n"
        f"- Agent: `{report.agent}`\n"
        f"- Timed out: `{report.timed_out}`\n"
        f"- Exit code: `{report.exit_code}`\n"
        f"- Run ID: `{report.final_run_id}`\n"
        f"- Verdict: `{report.final_verdict}`\n"
        f"- Reason: {report.reason}\n"
        f"- Run dir: `{report.final_run_dir}`\n"
        f"- Output log: `{report.output_log}`\n"
    )


def _batch_report_markdown(batch: BatchSupervisedReport) -> str:
    rows = [
        "| Scenario | Run ID | Verdict | Reason |",
        "|---|---:|---:|---|",
    ]
    for run in batch.runs:
        rows.append(
            f"| `{run['scenario_name']}` | `{run['run_id']}` | `{run['verdict']}` | {run['reason']} |",
        )
    return (
        "# Supervised Scenario Batch\n\n"
        f"- Scenario input: `{batch.scenario_input}`\n"
        f"- Tag: `{batch.tag or ''}`\n"
        f"- Agent: `{batch.agent}`\n"
        f"- Scenario count: `{batch.scenario_count}`\n"
        f"- Verdict counts: `{batch.verdict_counts}`\n"
        f"- Manifest: `{batch.manifest_path}`\n"
        f"- Exit code: `{batch.exit_code}`\n\n"
        + "\n".join(rows)
        + "\n"
    )


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def _default_command(scenario: Path, agent: str, qa_base: Path) -> list[str]:
    return [
        sys.executable,
        "-u",
        "-m",
        "benchmarks.ai_verification.run_scenario",
        "--scenario",
        str(scenario),
        "--agent",
        agent,
        "--base",
        str(qa_base),
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run an AI verification scenario with an outer timeout")
    parser.add_argument("--scenario", type=Path, required=True, help="Scenario file or directory")
    parser.add_argument("--agent", choices=["autocode", "codex", "claude"], required=True)
    parser.add_argument("--qa-base", type=Path, default=QA_BASE)
    parser.add_argument("--report-base", type=Path, default=Path("autocode/docs/qa/test-results/ai-verification-supervised"))
    parser.add_argument("--timeout-seconds", type=int, default=420)
    parser.add_argument("--tag", help="Optional tag/title/category/filename filter when --scenario is a directory")
    parser.add_argument(
        "--retry-schedule",
        default=",".join(f"{delay}s" for delay in DEFAULT_RETRY_SCHEDULE_SECONDS),
        help=(
            "Comma-separated transient-INFRA retry delays. Supports s/m/h suffixes. "
            "Default is the long recovery schedule requested by the user."
        ),
    )
    parser.add_argument(
        "--no-retry-transient-infra",
        action="store_true",
        help="Disable the default long transient-INFRA retry policy.",
    )
    parser.add_argument("--command", nargs=argparse.REMAINDER, help="Override child command after --")
    args = parser.parse_args()

    if args.scenario.is_dir():
        if args.command:
            parser.error("--command is only supported when --scenario is a file")
        batch = run_batch_supervised(
            scenario_input=args.scenario,
            tag=args.tag,
            agent=args.agent,
            qa_base=args.qa_base,
            report_base=args.report_base,
            timeout_seconds=args.timeout_seconds,
            retry_schedule_seconds=(
                [] if args.no_retry_transient_infra else parse_retry_schedule(args.retry_schedule)
            ),
        )
        print(json.dumps(asdict(batch), indent=2, default=str))
        print(f"[run_scenario_supervised] batch_manifest={batch.manifest_path}")
        raise SystemExit(batch.exit_code)

    command = args.command or _default_command(args.scenario, args.agent, args.qa_base)
    if command and command[0] == "--":
        command = command[1:]

    if args.no_retry_transient_infra:
        report = run_supervised(
            command=command,
            scenario_path=args.scenario,
            agent=args.agent,
            qa_base=args.qa_base,
            report_base=args.report_base,
            timeout_seconds=args.timeout_seconds,
        )
    else:
        report = run_supervised_with_retries(
            command=command,
            scenario_path=args.scenario,
            agent=args.agent,
            qa_base=args.qa_base,
            report_base=args.report_base,
            timeout_seconds=args.timeout_seconds,
            retry_schedule_seconds=parse_retry_schedule(args.retry_schedule),
        )
    print(json.dumps(asdict(report), indent=2, default=str))
    raise SystemExit(124 if report.timed_out else 0 if report.final_verdict != "UNKNOWN" else 1)


if __name__ == "__main__":
    main()
