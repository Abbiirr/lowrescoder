"""Build the AI verification harness dashboard.

Scans all run artifact dirs under QA_BASE, loads meta.json + grading_report.json +
scenario.json for each run, and writes:
  - autocode/docs/qa/test-results/ai-verification/index.md  (full table)
  - autocode/docs/qa/test-results/ai-verification/dashboard.md  (summary + trends)

Usage:
  uv run python -m benchmarks.ai_verification.build_dashboard
  uv run python -m benchmarks.ai_verification.build_dashboard --base <path>
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from benchmarks.ai_verification.schema import (
    QA_BASE,
    ScenarioSpec,
    GradingReport,
    RunMeta,
    Verdict,
)


def _load_run(run_dir: Path) -> tuple[ScenarioSpec, GradingReport, RunMeta] | None:
    try:
        scenario = ScenarioSpec.load(run_dir / "scenario.json")
        report_data = json.loads((run_dir / "grading_report.json").read_text())
        meta_data = json.loads((run_dir / "meta.json").read_text())
    except (FileNotFoundError, KeyError, json.JSONDecodeError):
        return None

    from benchmarks.ai_verification.schema import CheckResult, Check
    check_results = [
        CheckResult(
            check=Check(r["check"]),
            passed=r["passed"],
            command=r.get("command", ""),
            output=r.get("output", ""),
            exit_code=r.get("exit_code", 0),
        )
        for r in report_data.get("check_results", [])
    ]
    report = GradingReport(
        verdict=Verdict(report_data["verdict"]),
        check_results=check_results,
        ai_review_enabled=report_data.get("ai_review_enabled", False),
        ai_verdict=report_data.get("ai_verdict", ""),
        ai_reasoning=report_data.get("ai_reasoning", ""),
        ai_reviewer=report_data.get("ai_reviewer", ""),
    )
    meta = RunMeta(
        run_id=meta_data["run_id"],
        scenario_id=meta_data["scenario_id"],
        agent=meta_data["agent"],
        status=meta_data.get("status", report.verdict.value),
        started_at=meta_data["started_at"],
        finished_at=meta_data["finished_at"],
        wall_time_s=meta_data.get("wall_time_s", 0.0),
        exit_status=meta_data.get("exit_status", 0),
        tool_calls=meta_data.get("tool_calls", 0),
        tokens_in=meta_data.get("tokens_in", 0),
        tokens_out=meta_data.get("tokens_out", 0),
        error=meta_data.get("error", ""),
    )
    return scenario, report, meta


def build(base: Path | None = None) -> None:
    qa_base = base or QA_BASE

    runs: list[tuple[ScenarioSpec, GradingReport, RunMeta]] = []
    for run_dir in sorted(qa_base.iterdir()):
        if not run_dir.is_dir() or run_dir.name in (".", ".."):
            continue
        result = _load_run(run_dir)
        if result:
            runs.append(result)

    if not runs:
        print("[dashboard] no runs found")
        return

    _write_index(qa_base, runs)
    _write_dashboard(qa_base, runs)
    print(f"[dashboard] {len(runs)} runs indexed")


def _verdict_icon(v: Verdict) -> str:
    return {"PASS": "✅", "FAIL": "❌", "PARTIAL": "⚠️", "INFRA_FAIL": "🔧"}.get(v.value, "?")


def _write_index(qa_base: Path, runs: list) -> None:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# AI Verification Harness — Run Index",
        "",
        f"_Last updated: {now} — {len(runs)} runs total_",
        "",
        "| Run ID | Title | Category | Stack | Agent | Verdict | Checks | Wall Time |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for scenario, report, meta in sorted(runs, key=lambda r: r[2].started_at, reverse=True):
        icon = _verdict_icon(report.verdict)
        checks_passed = sum(1 for r in report.check_results if r.passed)
        checks_total = len(report.check_results)
        lines.append(
            f"| `{meta.run_id}` | {scenario.title[:40]} | {scenario.category.value} "
            f"| {scenario.target_stack.language} | {meta.agent} "
            f"| {icon} **{report.verdict.value}** | {checks_passed}/{checks_total} | {meta.wall_time_s:.1f}s |"
        )
    lines += ["", f"Artifacts: `{qa_base}/`"]
    (qa_base / "index.md").write_text("\n".join(lines))


def _write_dashboard(qa_base: Path, runs: list) -> None:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    total = len(runs)
    by_verdict: dict[str, int] = defaultdict(int)
    by_category: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    by_stack: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    by_difficulty: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    by_agent: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    total_wall: float = 0.0

    for scenario, report, meta in runs:
        v = report.verdict.value
        by_verdict[v] += 1
        by_category[scenario.category.value][v] += 1
        by_stack[scenario.target_stack.language][v] += 1
        by_difficulty[scenario.difficulty.value][v] += 1
        by_agent[meta.agent][v] += 1
        total_wall += meta.wall_time_s

    pass_rate = by_verdict.get("PASS", 0) / total * 100 if total else 0

    lines = [
        "# AI Verification Harness — Dashboard",
        "",
        f"_Last updated: {now}_",
        "",
        "## Overall",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Total runs | {total} |",
        f"| Pass rate | {pass_rate:.0f}% ({by_verdict.get('PASS', 0)}/{total}) |",
        f"| PASS | {by_verdict.get('PASS', 0)} |",
        f"| FAIL | {by_verdict.get('FAIL', 0)} |",
        f"| PARTIAL | {by_verdict.get('PARTIAL', 0)} |",
        f"| INFRA_FAIL | {by_verdict.get('INFRA_FAIL', 0)} |",
        f"| Total wall time | {total_wall:.1f}s |",
        "",
        "## By Category",
        "",
        "| Category | Total | PASS | FAIL | PARTIAL | INFRA_FAIL |",
        "|---|---|---|---|---|---|",
    ]
    for cat in sorted(by_category):
        d = by_category[cat]
        t = sum(d.values())
        lines.append(
            f"| {cat} | {t} | {d.get('PASS',0)} | {d.get('FAIL',0)} "
            f"| {d.get('PARTIAL',0)} | {d.get('INFRA_FAIL',0)} |"
        )

    lines += [
        "",
        "## By Stack",
        "",
        "| Stack | Total | PASS | FAIL |",
        "|---|---|---|---|",
    ]
    for stack in sorted(by_stack):
        d = by_stack[stack]
        t = sum(d.values())
        lines.append(f"| {stack} | {t} | {d.get('PASS',0)} | {d.get('FAIL',0)} |")

    lines += [
        "",
        "## By Difficulty",
        "",
        "| Difficulty | Total | PASS | FAIL |",
        "|---|---|---|---|",
    ]
    for diff in ("easy", "medium", "hard"):
        d = by_difficulty.get(diff, {})
        t = sum(d.values())
        if t:
            lines.append(f"| {diff} | {t} | {d.get('PASS',0)} | {d.get('FAIL',0)} |")

    lines += [
        "",
        "## By Agent",
        "",
        "| Agent | Total | PASS | FAIL |",
        "|---|---|---|---|",
    ]
    for agent in sorted(by_agent):
        d = by_agent[agent]
        t = sum(d.values())
        lines.append(f"| {agent} | {t} | {d.get('PASS',0)} | {d.get('FAIL',0)} |")

    (qa_base / "dashboard.md").write_text("\n".join(lines))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", type=Path, default=None)
    args = parser.parse_args()
    build(base=args.base)


if __name__ == "__main__":
    main()
