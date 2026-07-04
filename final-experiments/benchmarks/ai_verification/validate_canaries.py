"""Run fixture-validation against all canary scenarios.

For each scenario that uses a Python stack (or any runnable stack):
  - builds sandbox from fixture
  - runs deterministic checks (no agent)
  - writes artifacts
  - appends summary to index.md

Usage:
  uv run python benchmarks/ai_verification/validate_canaries.py
  uv run python benchmarks/ai_verification/validate_canaries.py --scenarios 01 02 03
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from benchmarks.ai_verification.run_scenario import run
from benchmarks.ai_verification.schema import QA_BASE, ScenarioSpec, Verdict

CANARY_DIR = Path("benchmarks/ai_verification/canary_scenarios")

RUNNABLE_STACKS = {"python", "go", "rust"}  # stacks we can validate locally


def _should_run(scenario: ScenarioSpec, filter_ids: list[str] | None) -> bool:
    if filter_ids:
        return any(scenario.scenario_id.endswith(sid) or scenario.title.lower().startswith(sid)
                   for sid in filter_ids)
    return scenario.target_stack.language in RUNNABLE_STACKS


def validate_all(filter_ids: list[str] | None = None) -> None:
    qa_base = QA_BASE
    qa_base.mkdir(parents=True, exist_ok=True)

    scenario_files = sorted(CANARY_DIR.glob("*.json"))
    results: list[dict] = []

    for sf in scenario_files:
        scenario = ScenarioSpec.load(sf)
        if not _should_run(scenario, filter_ids):
            print(f"[skip] {sf.name} (stack={scenario.target_stack.language})")
            continue

        print(f"\n{'='*60}")
        print(f"[validate] {sf.name}: {scenario.title}")
        try:
            run_id, report = run(
                scenario_path=sf,
                validate_fixture=True,
                keep_sandbox=False,
                qa_base=qa_base,
            )
            results.append({
                "scenario": sf.name,
                "title": scenario.title,
                "category": scenario.category.value,
                "stack": scenario.target_stack.language,
                "run_id": run_id,
                "verdict": report.verdict.value,
                "checks_passed": sum(1 for r in report.check_results if r.passed),
                "checks_total": len(report.check_results),
            })
        except Exception as exc:
            print(f"[ERROR] {sf.name}: {exc}")
            results.append({
                "scenario": sf.name,
                "title": scenario.title,
                "category": scenario.category.value,
                "stack": scenario.target_stack.language,
                "run_id": "n/a",
                "verdict": "INFRA_FAIL",
                "checks_passed": 0,
                "checks_total": 0,
                "error": str(exc),
            })

    _write_index(qa_base, results)
    _print_summary(results)


def _write_index(qa_base: Path, results: list[dict]) -> None:
    index_path = qa_base / "index.md"
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# AI Verification Harness — Run Index",
        "",
        f"_Last updated: {now}_",
        "",
        "| Scenario | Category | Stack | Run ID | Verdict | Checks |",
        "|---|---|---|---|---|---|",
    ]
    for r in results:
        checks = f"{r['checks_passed']}/{r['checks_total']}"
        lines.append(
            f"| {r['title']} | {r['category']} | {r['stack']} "
            f"| {r['run_id']} | **{r['verdict']}** | {checks} |"
        )
    lines += ["", "## Artifact Paths", "", f"All artifacts under `{qa_base}/`"]
    index_path.write_text("\n".join(lines))
    print(f"\n[index] written to {index_path}")


def _print_summary(results: list[dict]) -> None:
    pass_count = sum(1 for r in results if r["verdict"] == "PASS")
    fail_count = sum(1 for r in results if r["verdict"] == "FAIL")
    infra_count = sum(1 for r in results if r["verdict"] == "INFRA_FAIL")
    print(f"\n{'='*60}")
    print(f"Summary: {len(results)} scenarios  PASS={pass_count}  FAIL={fail_count}  INFRA_FAIL={infra_count}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenarios", nargs="*", help="Filter by scenario name prefix or id suffix")
    args = parser.parse_args()
    validate_all(args.scenarios)


if __name__ == "__main__":
    main()
