"""Run summary and cross-run reporting for AI verification harness.

Scans run directories and produces a summary table with verdict counts,
infra fail reasons, tool coverage, assertion failures, missing artifacts,
and slowest runs.

Usage:
    python -m benchmarks.ai_verification.summarize_runs [--base <path>]
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class RunSummary:
    run_id: str
    verdict: str
    primary_verdict: str = ""
    scenario_title: str = ""
    turn_count: int = 0
    tool_histogram: dict[str, int] = field(default_factory=dict)
    changed_files: list[str] = field(default_factory=list)
    infra_fail_reason: str = ""
    infra_signals: list[str] = field(default_factory=list)
    agent_fail_signals: list[str] = field(default_factory=list)
    missing_artifacts: list[str] = field(default_factory=list)
    assertion_failures: list[dict[str, str]] = field(default_factory=list)
    wall_time_s: float = 0.0


REQUIRED_NEW_ARTIFACTS = [
    "tool_calls.jsonl",
    "turns.json",
    "trajectory_report.json",
    "turn_report.json",
    "artifact_report.json",
    "run_summary.json",
    "grading_report.json",
    "meta.json",
]


def scan_run(run_dir: Path) -> RunSummary:
    summary = RunSummary(run_id=run_dir.name, verdict="UNKNOWN")

    meta_path = run_dir / "meta.json"
    if meta_path.is_file():
        try:
            meta = json.loads(meta_path.read_text())
            summary.verdict = meta.get("status", "UNKNOWN")
            summary.wall_time_s = meta.get("wall_time_s", 0.0)
        except (json.JSONDecodeError, ValueError):
            pass

    rs_path = run_dir / "run_summary.json"
    if rs_path.is_file():
        try:
            rs = json.loads(rs_path.read_text())
            summary.scenario_title = rs.get("scenario_title", "")
            summary.primary_verdict = rs.get("primary_verdict", "")
            summary.turn_count = rs.get("turn_count", 0)
            summary.tool_histogram = rs.get("tool_histogram", {})
            summary.changed_files = rs.get("changed_files", [])
            summary.infra_fail_reason = rs.get("infra_fail_reason", "")
            summary.infra_signals = rs.get("infra_signals", [])
            summary.agent_fail_signals = rs.get("agent_fail_signals", [])
        except (json.JSONDecodeError, ValueError):
            pass

    for artifact in REQUIRED_NEW_ARTIFACTS:
        if not (run_dir / artifact).is_file():
            summary.missing_artifacts.append(artifact)

    summary.assertion_failures = _collect_assertion_failures(run_dir)
    return summary


def _collect_assertion_failures(run_dir: Path) -> list[dict[str, str]]:
    failures: list[dict[str, str]] = []
    for filename in ("trajectory_report.json", "turn_report.json", "artifact_report.json"):
        path = run_dir / filename
        if not path.is_file():
            continue
        try:
            report = json.loads(path.read_text())
        except (json.JSONDecodeError, ValueError):
            continue
        results = report.get("results", [])
        if not isinstance(results, list):
            continue
        for result in results:
            if not isinstance(result, dict) or result.get("passed", True):
                continue
            failures.append({
                "run_id": run_dir.name,
                "source": filename,
                "assertion": str(result.get("assertion", "")),
                "detail": str(result.get("detail", "")),
            })
    return failures


def summarize_all(base: Path, run_ids: set[str] | None = None) -> dict[str, Any]:
    runs: list[RunSummary] = []
    if not base.is_dir():
        return {"error": f"base path not found: {base}", "runs": []}

    for run_dir in sorted(base.iterdir()):
        if run_ids is not None and run_dir.name not in run_ids:
            continue
        if run_dir.is_dir() and (run_dir / "meta.json").is_file():
            runs.append(scan_run(run_dir))

    verdict_counts: dict[str, int] = {}
    infra_reasons: dict[str, int] = {}
    assertion_failures: list[dict[str, str]] = []
    missing_artifacts_count = 0
    tool_coverage: dict[str, int] = {}

    for run in runs:
        verdict_counts[run.verdict] = verdict_counts.get(run.verdict, 0) + 1
        if run.infra_fail_reason:
            infra_reasons[run.infra_fail_reason] = infra_reasons.get(run.infra_fail_reason, 0) + 1
        if run.missing_artifacts:
            missing_artifacts_count += 1
        assertion_failures.extend(run.assertion_failures)
        for tool, count in run.tool_histogram.items():
            tool_coverage[tool] = tool_coverage.get(tool, 0) + count

    slowest = sorted(runs, key=lambda r: r.wall_time_s, reverse=True)[:5]

    return {
        "total_runs": len(runs),
        "verdict_counts": verdict_counts,
        "infra_fail_reasons": infra_reasons,
        "tool_coverage": tool_coverage,
        "assertion_failures": assertion_failures,
        "runs_with_missing_artifacts": missing_artifacts_count,
        "slowest_runs": [
            {"run_id": r.run_id, "verdict": r.verdict, "wall_time_s": r.wall_time_s}
            for r in slowest
        ],
        "runs": [
            {
                "run_id": r.run_id,
                "verdict": r.verdict,
                "primary_verdict": r.primary_verdict,
                "scenario": r.scenario_title,
                "turns": r.turn_count,
                "tools": r.tool_histogram,
                "changed_files": r.changed_files,
                "infra_fail_reason": r.infra_fail_reason,
                "infra_signals": r.infra_signals,
                "agent_fail_signals": r.agent_fail_signals,
                "missing_artifacts": r.missing_artifacts,
                "wall_time_s": r.wall_time_s,
            }
            for r in runs
        ],
    }


def summarize_batch_manifest(manifest_path: Path) -> dict[str, Any]:
    """Summarize only run directories listed in a batch manifest."""

    manifest = json.loads(Path(manifest_path).read_text())
    run_dirs: list[Path] = []
    for run in manifest.get("runs", []):
        if not isinstance(run, dict):
            continue
        run_dir = run.get("run_dir")
        if run_dir:
            run_dirs.append(Path(str(run_dir)))
    return _summarize_runs([scan_run(run_dir) for run_dir in run_dirs if run_dir.is_dir()])


def _summarize_runs(runs: list[RunSummary]) -> dict[str, Any]:
    verdict_counts: dict[str, int] = {}
    infra_reasons: dict[str, int] = {}
    assertion_failures: list[dict[str, str]] = []
    missing_artifacts_count = 0
    tool_coverage: dict[str, int] = {}

    for run in runs:
        verdict_counts[run.verdict] = verdict_counts.get(run.verdict, 0) + 1
        if run.infra_fail_reason:
            infra_reasons[run.infra_fail_reason] = infra_reasons.get(run.infra_fail_reason, 0) + 1
        if run.missing_artifacts:
            missing_artifacts_count += 1
        assertion_failures.extend(run.assertion_failures)
        for tool, count in run.tool_histogram.items():
            tool_coverage[tool] = tool_coverage.get(tool, 0) + count

    slowest = sorted(runs, key=lambda r: r.wall_time_s, reverse=True)[:5]

    return {
        "total_runs": len(runs),
        "verdict_counts": verdict_counts,
        "infra_fail_reasons": infra_reasons,
        "tool_coverage": tool_coverage,
        "assertion_failures": assertion_failures,
        "runs_with_missing_artifacts": missing_artifacts_count,
        "slowest_runs": [
            {"run_id": r.run_id, "verdict": r.verdict, "wall_time_s": r.wall_time_s}
            for r in slowest
        ],
        "runs": [
            {
                "run_id": r.run_id,
                "verdict": r.verdict,
                "scenario": r.scenario_title,
                "turns": r.turn_count,
                "tools": r.tool_histogram,
                "changed_files": r.changed_files,
                "infra_fail_reason": r.infra_fail_reason,
                "missing_artifacts": r.missing_artifacts,
                "wall_time_s": r.wall_time_s,
            }
            for r in runs
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize AI verification run results")
    parser.add_argument("--base", type=Path, default=Path("autocode/docs/qa/test-results/ai-verification"))
    parser.add_argument(
        "--batch-manifest",
        type=Path,
        help="Summarize only run directories listed in a supervised batch_manifest.json.",
    )
    parser.add_argument(
        "--run-id",
        action="append",
        default=[],
        help="Only include a specific run id. May be repeated.",
    )
    parser.add_argument(
        "--run-ids",
        default="",
        help="Comma-separated run ids to include in this summary.",
    )
    args = parser.parse_args()

    if args.batch_manifest:
        print(json.dumps(summarize_batch_manifest(args.batch_manifest), indent=2, default=str))
        return

    selected = set(args.run_id)
    if args.run_ids:
        selected.update(item.strip() for item in args.run_ids.split(",") if item.strip())
    result = summarize_all(args.base, run_ids=selected or None)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
