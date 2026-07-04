"""Simulate an agent run by applying a known-good solution to a sandbox.

Used for end-to-end pipeline testing (Milestone 6 proxy):
  - Builds sandbox from scenario fixture
  - Applies a solution directory (writes files into sandbox)
  - Runs full grading pipeline
  - Stores artifacts as if a real agent had run

Solution directories live under benchmarks/ai_verification/solutions/<scenario_id>/
Each solution dir contains files to write relative to the sandbox root.

Usage:
  uv run python -m benchmarks.ai_verification.simulate_agent_run \\
    --scenario benchmarks/ai_verification/canary_scenarios/01_backend_health_endpoint.json

  uv run python -m benchmarks.ai_verification.simulate_agent_run \\
    --scenario benchmarks/ai_verification/canary_scenarios/02_refactor_extract_function.json \\
    --keep-sandbox
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from benchmarks.ai_verification.sandbox_builder import build_sandbox, snapshot_repo, teardown_sandbox
from benchmarks.ai_verification.schema import (
    GradingReport,
    QA_BASE,
    RunMeta,
    ScenarioSpec,
    Verdict,
    artifact_dir,
    new_run_id,
    sandbox_dir,
)

SOLUTIONS_DIR = Path("benchmarks/ai_verification/solutions")


def simulate(
    scenario_path: Path,
    qa_base: Path | None = None,
    keep_sandbox: bool = False,
    ai_review: bool = False,
) -> tuple[str, GradingReport]:
    from benchmarks.ai_verification.run_scenario import _run_checks, _capture_diff

    qa_base = qa_base or QA_BASE
    scenario = ScenarioSpec.load(scenario_path)
    solution_dir = SOLUTIONS_DIR / scenario.scenario_id

    if not solution_dir.exists():
        print(f"[simulate] no solution found at {solution_dir} — use --validate-fixture instead")
        sys.exit(1)

    run_id = new_run_id()
    arts = artifact_dir(run_id, qa_base)
    arts.mkdir(parents=True, exist_ok=True)
    sandbox = sandbox_dir(run_id)

    started_at = datetime.now(timezone.utc).isoformat()
    t0 = time.monotonic()

    print(f"[simulate] run_id={run_id}")
    print(f"[simulate] scenario={scenario.title!r} ({scenario.category.value})")
    print(f"[simulate] applying solution from {solution_dir}")

    scenario.save(arts / "scenario.json")

    # Build sandbox from fixture
    build_sandbox(scenario.repo_seed, sandbox)
    snapshot_repo(sandbox, arts / "repo_seed")

    # Apply solution files
    applied = _apply_solution(solution_dir, sandbox)
    print(f"[simulate] applied {len(applied)} solution files: {applied}")

    # Capture what "the agent" changed
    _capture_diff(sandbox, arts / "diff.patch")

    # Run grading checks
    check_results, test_log = _run_checks(scenario, sandbox)
    (arts / "test_log.txt").write_text(test_log)

    all_passed = all(r.passed for r in check_results)
    if not check_results:
        verdict = Verdict.INFRA_FAIL
    elif all_passed:
        verdict = Verdict.PASS
    elif any(r.passed for r in check_results):
        verdict = Verdict.PARTIAL
    else:
        verdict = Verdict.FAIL

    # Optional AI review
    ai_verdict_str = ""
    ai_reasoning = ""
    if ai_review and all_passed and scenario.grading.ai_review_enabled:
        from benchmarks.ai_verification.grade_run import _run_ai_review
        ai_verdict_str, ai_reasoning = _run_ai_review(arts, scenario)
    else:
        (arts / "review.md").write_text(
            "# AI Review\n\nSkipped (pass `--ai-review` to enable, requires gateway)\n"
        )

    report = GradingReport(
        verdict=verdict,
        check_results=check_results,
        ai_review_enabled=ai_review,
        ai_verdict=ai_verdict_str,
        ai_reasoning=ai_reasoning,
        ai_reviewer=scenario.grading.reviewer if ai_verdict_str else "",
    )
    report.save(arts / "grading_report.json")

    # Fake transcript (known solution, not a real agent)
    transcript = [
        {"role": "system", "content": "simulate_agent_run: known-good solution applied"},
        {"role": "files_written", "content": json.dumps(applied)},
    ]
    (arts / "agent_transcript.jsonl").write_text("\n".join(json.dumps(t) for t in transcript))

    finished_at = datetime.now(timezone.utc).isoformat()
    wall_time_s = time.monotonic() - t0
    meta = RunMeta(
        run_id=run_id,
        scenario_id=scenario.scenario_id,
        agent="simulate-known-solution",
        status=verdict.value,
        started_at=started_at,
        finished_at=finished_at,
        wall_time_s=round(wall_time_s, 2),
        exit_status=0 if all_passed else 1,
    )
    meta.save(arts / "meta.json")

    if not keep_sandbox:
        teardown_sandbox(sandbox)

    print(f"[simulate] verdict={verdict.value}  wall_time={wall_time_s:.1f}s")
    print(f"[simulate] artifacts at {arts}")
    for r in check_results:
        status = "PASS" if r.passed else "FAIL"
        print(f"  [{status}] {r.check.value}")
    return run_id, report


def _apply_solution(solution_dir: Path, sandbox: Path) -> list[str]:
    applied = []
    for src in solution_dir.rglob("*"):
        if src.is_file():
            rel = src.relative_to(solution_dir)
            dst = sandbox / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            applied.append(str(rel))
    return applied


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulate agent run with known solution")
    parser.add_argument("--scenario", type=Path, required=True)
    parser.add_argument("--keep-sandbox", action="store_true")
    parser.add_argument("--ai-review", action="store_true")
    parser.add_argument("--base", type=Path, default=None)
    args = parser.parse_args()
    simulate(
        scenario_path=args.scenario,
        qa_base=args.base,
        keep_sandbox=args.keep_sandbox,
        ai_review=args.ai_review,
    )


if __name__ == "__main__":
    main()
