#!/usr/bin/env python3
"""Generic scenario runner for E2E benchmarks.

Reuses core infrastructure from the calculator benchmark:
- SandboxProcessTracker for process management
- BenchmarkLogger for event logging
- BenchmarkVerdict for result classification
- _benchmark_run_command for safe command execution

Usage:
    uv run python scripts/e2e/run_scenario.py E2E-BugFix
    uv run python scripts/e2e/run_scenario.py E2E-CLI
    uv run python scripts/e2e/run_scenario.py --list
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from e2e.scenario_contract import ScenarioManifest  # noqa: E402
from e2e.scoring import (  # noqa: E402
    check_required_files,
    run_acceptance_checks,
    score_scenario,
)

# Import infrastructure from calculator benchmark (not duplicated)
import run_calculator_benchmark as rcb  # noqa: E402

from hybridcoder.agent.approval import ApprovalManager, ApprovalMode  # noqa: E402
from hybridcoder.agent.loop import AgentLoop  # noqa: E402
from hybridcoder.agent.tools import create_default_registry  # noqa: E402
from hybridcoder.config import ShellConfig, load_config  # noqa: E402
from hybridcoder.layer4.llm import create_provider  # noqa: E402
from hybridcoder.session.store import SessionStore  # noqa: E402

# Scenario registry — import manifests
from e2e.scenarios.bugfix import MANIFEST as BUGFIX_MANIFEST  # noqa: E402
from e2e.scenarios.cli_tool import MANIFEST as CLI_MANIFEST  # noqa: E402

SCENARIO_REGISTRY: dict[str, ScenarioManifest] = {
    BUGFIX_MANIFEST.scenario_id: BUGFIX_MANIFEST,
    CLI_MANIFEST.scenario_id: CLI_MANIFEST,
}

API_RETRY_COOLDOWN = 60
MAX_API_RETRIES = 3
MAX_TOOL_TIMEOUT = 120

RESULTS_DIR = PROJECT_ROOT / "docs" / "qa" / "test-results"


# --- Manifest Validation (S3) ---


class ManifestValidationError(ValueError):
    """Raised when a scenario manifest fails validation."""


def validate_manifest(manifest: ScenarioManifest) -> None:
    """Fail-fast validation of a scenario manifest.

    Checks: scenario_id, prompt, budgets > 0, seed_fixture exists,
    acceptance_checks non-empty.
    """
    errors: list[str] = []

    if not manifest.scenario_id:
        errors.append("scenario_id is empty")
    if not manifest.prompt:
        errors.append("prompt is empty")
    if manifest.max_wall_time_s <= 0:
        errors.append(f"max_wall_time_s must be > 0, got {manifest.max_wall_time_s}")
    if manifest.max_tool_calls <= 0:
        errors.append(f"max_tool_calls must be > 0, got {manifest.max_tool_calls}")
    if manifest.max_turns <= 0:
        errors.append(f"max_turns must be > 0, got {manifest.max_turns}")
    if not manifest.acceptance_checks:
        errors.append("acceptance_checks is empty — at least one check required")
    if manifest.seed_fixture is not None and not manifest.seed_fixture.exists():
        errors.append(f"seed_fixture does not exist: {manifest.seed_fixture}")

    if errors:
        raise ManifestValidationError(
            f"Manifest '{manifest.scenario_id}' failed validation:\n"
            + "\n".join(f"  - {e}" for e in errors)
        )


# --- Sandbox Setup ---


class SetupError(RuntimeError):
    """Raised when a sandbox setup command fails."""


def setup_sandbox(sandbox: Path, manifest: ScenarioManifest) -> None:
    """Copy seed fixture into sandbox and run setup commands.

    Raises SetupError if any setup command fails — this should be
    classified as INFRA_FAIL, not a product FAIL.
    """
    if manifest.seed_fixture is not None:
        print(f"  Seeding sandbox from {manifest.seed_fixture.name}/")
        # Copy all files from seed fixture into sandbox
        for item in manifest.seed_fixture.iterdir():
            if item.name == "node_modules":
                continue  # Never copy node_modules from fixtures
            dest = sandbox / item.name
            if item.is_dir():
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)

    for cmd in manifest.setup_commands:
        print(f"  Running setup: {cmd}")
        import subprocess

        result = subprocess.run(
            cmd,
            shell=True,  # noqa: S602
            cwd=sandbox,
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
        if result.returncode != 0:
            stderr_preview = result.stderr[:500] if result.stderr else "(no stderr)"
            raise SetupError(
                f"Setup command failed: '{cmd}' (exit {result.returncode})\n"
                f"  stderr: {stderr_preview}"
            )


# --- Agent Execution ---


async def run_agent_for_scenario(
    sandbox: Path,
    manifest: ScenarioManifest,
    bench_log: rcb.BenchmarkLogger,
) -> dict:
    """Run the AgentLoop for a scenario with budget enforcement."""
    config = load_config(project_root=PROJECT_ROOT)

    config.shell.enabled = True
    config.shell.timeout = 120
    config.shell.max_timeout = 300
    config.shell.allow_network = True
    config.shell.allowed_commands = [
        "npm", "npx", "node", "git", "mkdir", "ls", "cat", "echo",
        "pytest", "python", "pip", "uv", "ruff", "mypy",
    ]
    config.tui.approval_mode = "auto"

    original_max = AgentLoop.MAX_ITERATIONS
    AgentLoop.MAX_ITERATIONS = manifest.max_tool_calls

    original_cwd = os.getcwd()
    os.chdir(sandbox)

    try:
        provider = create_provider(config)
        registry = create_default_registry(project_root=str(sandbox))

        # Replace run_command with benchmark-safe handler
        run_cmd_tool = registry.get("run_command")
        if run_cmd_tool:
            run_cmd_tool.handler = rcb._benchmark_run_command

        shell_config = ShellConfig(
            enabled=True,
            timeout=120,
            max_timeout=300,
            allow_network=True,
            allowed_commands=config.shell.allowed_commands,
            blocked_commands=["rm -rf /", "rm -rf ~", "sudo"],
        )
        approval_mgr = ApprovalManager(ApprovalMode.AUTO, shell_config)

        db_path = sandbox / ".benchmark-sessions.db"
        session_store = SessionStore(db_path)
        session_id = session_store.create_session(
            title=f"E2E Benchmark: {manifest.name}",
            model=config.llm.model,
            provider=config.llm.provider,
            project_dir=str(sandbox),
        )

        loop = AgentLoop(
            provider=provider,
            tool_registry=registry,
            approval_manager=approval_mgr,
            session_store=session_store,
            session_id=session_id,
        )

        # Callbacks
        tool_call_count = 0
        start_time = time.monotonic()

        def on_chunk(text: str) -> None:
            bench_log.text_chunks.append(text)

        def on_thinking_chunk(text: str) -> None:
            bench_log.log("thinking", text=text[:200])

        def on_tool_call(name: str, status: str, result: str) -> None:
            nonlocal tool_call_count
            if status == "running":
                tool_call_count += 1
            bench_log.tool_calls.append({
                "name": name, "status": status, "result": result[:500],
            })
            bench_log.log(
                "tool_call", name=name, status=status, result_preview=result[:200],
            )
            if status in ("running", "completed"):
                print(f"  [{tool_call_count:3d}] {name}: {status}", flush=True)

        async def approval_callback(
            tool_name: str, arguments: dict,
        ) -> bool:
            bench_log.log("approval", tool_name=tool_name, approved=True)
            return True

        async def ask_user_callback(
            question: str, options: list[str], allow_text: bool,
        ) -> str:
            if options:
                answer = options[0]
            else:
                answer = "Proceed with your best judgment."
            bench_log.ask_user_questions.append({
                "question": question, "options": options, "answer": answer,
            })
            bench_log.log("ask_user", question=question[:200], answer=answer)
            print(f"  [ask_user] Q: {question[:80]} -> A: {answer}", flush=True)
            return answer

        async def _run_turn(
            prompt: str, turn_num: int, tc_before: int,
        ) -> dict:
            nonlocal tool_call_count
            retries = 0

            # S2: Budget enforcement — check before each turn
            elapsed = time.monotonic() - start_time
            if elapsed > manifest.max_wall_time_s:
                return {
                    "turn": turn_num, "prompt": prompt,
                    "result_preview": "[Budget exceeded: wall time]",
                    "duration_s": 0, "tool_calls": 0,
                    "hit_max_iterations": False, "api_retries": 0,
                    "error": "wall_time_budget_exceeded",
                }
            if tool_call_count >= manifest.max_tool_calls:
                return {
                    "turn": turn_num, "prompt": prompt,
                    "result_preview": "[Budget exceeded: tool calls]",
                    "duration_s": 0, "tool_calls": 0,
                    "hit_max_iterations": False, "api_retries": 0,
                    "error": "tool_call_budget_exceeded",
                }

            while True:
                turn_start = time.monotonic()
                try:
                    bench_log.log(
                        "turn_start", turn=turn_num, prompt=prompt[:200],
                        retry=retries,
                    )
                    result = await loop.run(
                        prompt,
                        on_chunk=on_chunk,
                        on_thinking_chunk=on_thinking_chunk,
                        on_tool_call=on_tool_call,
                        approval_callback=approval_callback,
                        ask_user_callback=ask_user_callback,
                    )
                    turn_duration = time.monotonic() - turn_start
                    turn_data = {
                        "turn": turn_num,
                        "prompt": prompt,
                        "result_preview": result[:500],
                        "duration_s": round(turn_duration, 1),
                        "tool_calls": tool_call_count - tc_before,
                        "hit_max_iterations": "[Max iterations reached]" in result,
                        "api_retries": retries,
                        "error": None,
                    }
                    bench_log.log(
                        "turn_end", turn=turn_num,
                        duration_s=round(turn_duration, 1),
                    )
                    print(
                        f"  Turn {turn_num} complete: {round(turn_duration, 1)}s, "
                        f"{tool_call_count - tc_before} tool calls"
                        f"{f' ({retries} retries)' if retries else ''}",
                        flush=True,
                    )
                    return turn_data
                except Exception as e:
                    turn_duration = time.monotonic() - turn_start
                    error_msg = str(e)
                    bench_log.log(
                        "api_error", turn=turn_num, error=error_msg,
                        retry=retries, tool_calls_so_far=tool_call_count,
                    )

                    if retries >= MAX_API_RETRIES:
                        print(
                            f"\n  Turn {turn_num} FAILED after {retries} retries: "
                            f"{error_msg[:100]}",
                            flush=True,
                        )
                        return {
                            "turn": turn_num,
                            "prompt": prompt,
                            "result_preview": f"[API Error: {error_msg[:200]}]",
                            "duration_s": round(turn_duration, 1),
                            "tool_calls": tool_call_count - tc_before,
                            "hit_max_iterations": False,
                            "api_retries": retries,
                            "error": error_msg,
                        }

                    retries += 1
                    cooldown = API_RETRY_COOLDOWN * retries
                    print(
                        f"\n  API error on turn {turn_num}: {error_msg[:80]}"
                        f"\n  Waiting {cooldown}s before retry "
                        f"{retries}/{MAX_API_RETRIES}...",
                        flush=True,
                    )
                    await asyncio.sleep(cooldown)

                    prompt = "Continue where you left off."
                    print(
                        f"\n--- Turn {turn_num} retry {retries}: "
                        f"Continuing after cooldown ---",
                        flush=True,
                    )

        # Run main prompt
        turns = []
        print(f"\n--- Turn 1: {manifest.scenario_id} initial prompt ---", flush=True)
        turn_data = await _run_turn(manifest.prompt, turn_num=1, tc_before=0)
        turns.append(turn_data)

        # Follow-up turns — always execute per manifest (verification steps)
        # Stop only if budget exceeded or turn limit reached
        for i, followup in enumerate(manifest.follow_ups):
            if i + 2 > manifest.max_turns:
                break

            last = turns[-1]
            # Stop if last turn had a real API error with no progress
            if last.get("error") and last["tool_calls"] == 0:
                break

            turn_num = i + 2
            tc_before = tool_call_count

            print(f"\n--- Turn {turn_num}: Follow-up ---", flush=True)
            turn_data = await _run_turn(
                followup, turn_num=turn_num, tc_before=tc_before,
            )
            turns.append(turn_data)

        session_store.close()

        return {
            "turns": turns,
            "total_tool_calls": tool_call_count,
            "total_ask_user": len(bench_log.ask_user_questions),
            "total_duration_s": round(sum(t["duration_s"] for t in turns), 1),
            "model": config.llm.model,
            "provider": config.llm.provider,
        }
    finally:
        os.chdir(original_cwd)
        AgentLoop.MAX_ITERATIONS = original_max


# --- Budget Checking ---


def check_budgets_for_scenario(
    agent_result: dict, manifest: ScenarioManifest,
) -> dict:
    """Check if the scenario stayed within manifest budget limits."""
    wall_time = agent_result.get("total_duration_s", 0)
    tool_calls = agent_result.get("total_tool_calls", 0)
    turns = len(agent_result.get("turns", []))

    return {
        "wall_time": {
            "value": wall_time,
            "limit": manifest.max_wall_time_s,
            "passed": wall_time <= manifest.max_wall_time_s,
        },
        "tool_calls": {
            "value": tool_calls,
            "limit": manifest.max_tool_calls,
            "passed": tool_calls <= manifest.max_tool_calls,
        },
        "turns": {
            "value": turns,
            "limit": manifest.max_turns,
            "passed": turns <= manifest.max_turns,
        },
    }


# --- Verdict Classification ---


def classify_scenario_result(
    scores: dict,
    check_results: list[dict],
    agent_result: dict,
    manifest: ScenarioManifest,
    budgets: dict | None = None,
) -> tuple[str, list[str]]:
    """Classify scenario result as PASS, FAIL, or INFRA_FAIL."""
    reasons: list[str] = []

    # API/infra errors → INFRA_FAIL
    turns = agent_result.get("turns", [])
    api_errors = [t for t in turns if t.get("error")]
    # Budget exceeded errors are not infra failures
    real_api_errors = [
        t for t in api_errors
        if t.get("error") not in ("wall_time_budget_exceeded", "tool_call_budget_exceeded")
    ]
    if real_api_errors:
        reasons.append(f"API errors in {len(real_api_errors)} turn(s)")
        return rcb.BenchmarkVerdict.INFRA_FAIL, reasons

    # Budget violations → FAIL
    if budgets:
        for budget_name, info in budgets.items():
            if not info["passed"]:
                reasons.append(
                    f"Budget exceeded: {budget_name} "
                    f"({info['value']} > {info['limit']})"
                )

    # Required acceptance check failures → FAIL
    for cr in check_results:
        if cr["required"] and not cr["passed"]:
            reasons.append(f"Required check '{cr['name']}' failed")

    # Score below minimum → FAIL
    total = scores.get("total", 0)
    if total < manifest.min_score:
        reasons.append(f"Score {total} < minimum {manifest.min_score}")

    if reasons:
        return rcb.BenchmarkVerdict.FAIL, reasons

    return rcb.BenchmarkVerdict.PASS, []


# --- Reporting ---


def generate_scenario_report(
    manifest: ScenarioManifest,
    agent_result: dict,
    check_results: list[dict],
    scores: dict,
    verdict: str,
    verdict_reasons: list[str],
    budgets: dict,
    trace_analysis: dict,
    sandbox: Path,
) -> str:
    """Generate a markdown report for a scenario run."""
    ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        f"# E2E Benchmark Report: {manifest.name}",
        f"**Scenario:** {manifest.scenario_id}  ",
        f"**Date:** {ts}  ",
        f"**Verdict:** {verdict}  ",
        f"**Score:** {scores.get('total', 0)}/{scores.get('max_score', 100)}  ",
        f"**Model:** {agent_result.get('model', 'unknown')}  ",
        f"**Provider:** {agent_result.get('provider', 'unknown')}  ",
        "",
        "## Acceptance Checks",
        "",
        "| Check | Status | Required | Exit Code |",
        "|-------|--------|----------|-----------|",
    ]

    for cr in check_results:
        status = "PASS" if cr["passed"] else "FAIL"
        req = "Yes" if cr["required"] else "No"
        lines.append(f"| {cr['name']} | {status} | {req} | {cr['exit_code']} |")

    lines.extend([
        "",
        "## Scores",
        "",
    ])
    for key, val in scores.items():
        if key not in ("missing_files",):
            lines.append(f"- **{key}:** {val}")

    missing = scores.get("missing_files", [])
    if missing:
        lines.extend(["", "### Missing Required Files", ""])
        for f in missing:
            lines.append(f"- `{f}`")

    lines.extend([
        "",
        "## Budgets",
        "",
        "| Budget | Value | Limit | Status |",
        "|--------|-------|-------|--------|",
    ])
    for name, info in budgets.items():
        status = "OK" if info["passed"] else "EXCEEDED"
        lines.append(f"| {name} | {info['value']} | {info['limit']} | {status} |")

    lines.extend([
        "",
        "## Agent Execution",
        "",
        f"- **Total tool calls:** {agent_result.get('total_tool_calls', 0)}",
        f"- **Total duration:** {agent_result.get('total_duration_s', 0)}s",
        f"- **Turns:** {len(agent_result.get('turns', []))}",
    ])

    if verdict_reasons:
        lines.extend(["", "## Verdict Reasons", ""])
        for r in verdict_reasons:
            lines.append(f"- {r}")

    if trace_analysis.get("warnings"):
        lines.extend(["", "## Trace Warnings", ""])
        for w in trace_analysis["warnings"]:
            lines.append(f"- {w}")

    lines.extend([
        "",
        f"**Sandbox:** `{sandbox}`  ",
    ])

    return "\n".join(lines)


def save_scenario_results(
    manifest: ScenarioManifest,
    report: str,
    agent_result: dict,
    check_results: list[dict],
    scores: dict,
    verdict: str,
    verdict_reasons: list[str],
    budgets: dict,
) -> Path:
    """Save scenario results to docs/qa/test-results/."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = manifest.scenario_id.lower().replace("-", "_")

    # Save markdown report
    report_path = RESULTS_DIR / f"{ts}-e2e-{slug}.md"
    report_path.write_text(report, encoding="utf-8")

    # Save JSON results
    json_path = RESULTS_DIR / f"{ts}-e2e-{slug}.json"
    results = {
        "scenario_id": manifest.scenario_id,
        "timestamp": datetime.now(UTC).isoformat(),
        "verdict": verdict,
        "verdict_reasons": verdict_reasons,
        "scores": scores,
        "check_results": check_results,
        "budgets": budgets,
        "agent_summary": {
            "model": agent_result.get("model"),
            "provider": agent_result.get("provider"),
            "total_tool_calls": agent_result.get("total_tool_calls"),
            "total_duration_s": agent_result.get("total_duration_s"),
            "turns": len(agent_result.get("turns", [])),
        },
    }
    json_path.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")

    print(f"\n  Report saved: {report_path}")
    print(f"  Results saved: {json_path}")
    return report_path


# --- Full Orchestration ---


async def run_scenario(manifest: ScenarioManifest) -> dict:
    """Run a single E2E scenario end-to-end.

    Phases: A (prerequisites) → B (sandbox + seed) → C (agent) →
            D (acceptance checks) → E (scoring) → F (classify + report + save)
    """
    print(f"\n{'='*60}")
    print(f"  E2E Scenario: {manifest.name} ({manifest.scenario_id})")
    print(f"{'='*60}")

    # Phase A: Prerequisites
    print("\n[Phase A] Checking prerequisites...")
    rcb.check_prerequisites()

    # Phase B: Sandbox + seed
    print("\n[Phase B] Creating sandbox...")
    rcb.clean_old_sandboxes()
    sandbox = rcb.create_sandbox()
    print(f"  Sandbox: {sandbox}")

    tracker = rcb.SandboxProcessTracker(sandbox)
    rcb._active_tracker = tracker

    log_path = sandbox / "benchmark.jsonl"
    bench_log = rcb.BenchmarkLogger(log_path)

    try:
        bench_log.log("scenario_start", scenario_id=manifest.scenario_id)
        try:
            setup_sandbox(sandbox, manifest)
        except SetupError as e:
            bench_log.log("setup_error", error=str(e))
            bench_log.close()
            print(f"\n  SETUP ERROR: {e}")
            return {
                "scenario_id": manifest.scenario_id,
                "verdict": rcb.BenchmarkVerdict.INFRA_FAIL,
                "verdict_reasons": [f"Setup failed: {e}"],
                "scores": {"total": 0},
                "sandbox": str(sandbox),
            }

        # Phase C: Agent execution
        print("\n[Phase C] Running agent...")
        agent_result = await run_agent_for_scenario(sandbox, manifest, bench_log)
        bench_log.log(
            "agent_done",
            tool_calls=agent_result.get("total_tool_calls"),
            duration_s=agent_result.get("total_duration_s"),
        )

        # Phase D: Acceptance checks
        print("\n[Phase D] Running acceptance checks...")
        check_results = run_acceptance_checks(sandbox, manifest)
        for cr in check_results:
            status = "PASS" if cr["passed"] else "FAIL"
            print(f"  {cr['name']}: {status}")
        bench_log.log("checks_done", results=[
            {"name": c["name"], "passed": c["passed"]} for c in check_results
        ])

        # Phase E: Scoring
        print("\n[Phase E] Scoring...")
        scores = score_scenario(sandbox, manifest, check_results)
        print(f"  Total score: {scores.get('total', 0)}/{scores.get('max_score', 100)}")
        bench_log.log("scoring_done", scores=scores)

        # Phase F: Classify + report + save
        print("\n[Phase F] Classifying result...")
        budgets = check_budgets_for_scenario(agent_result, manifest)
        trace_analysis = rcb.analyze_trace(log_path)
        verdict, reasons = classify_scenario_result(
            scores, check_results, agent_result, manifest, budgets,
        )
        print(f"  Verdict: {verdict}")
        if reasons:
            for r in reasons:
                print(f"    - {r}")

        report = generate_scenario_report(
            manifest, agent_result, check_results, scores,
            verdict, reasons, budgets, trace_analysis, sandbox,
        )
        save_scenario_results(
            manifest, report, agent_result, check_results,
            scores, verdict, reasons, budgets,
        )

        bench_log.log("scenario_end", verdict=verdict)
        bench_log.close()

        return {
            "scenario_id": manifest.scenario_id,
            "verdict": verdict,
            "verdict_reasons": reasons,
            "scores": scores,
            "check_results": check_results,
            "budgets": budgets,
            "agent_result": agent_result,
            "sandbox": str(sandbox),
        }

    except Exception as e:
        bench_log.log("scenario_error", error=str(e))
        bench_log.close()
        print(f"\n  ERROR: {e}")
        return {
            "scenario_id": manifest.scenario_id,
            "verdict": rcb.BenchmarkVerdict.INFRA_FAIL,
            "verdict_reasons": [str(e)],
            "scores": {"total": 0},
            "sandbox": str(sandbox),
        }
    finally:
        tracker.kill_all()
        rcb._active_tracker = None


# --- CLI Entry Point ---


def list_scenarios() -> None:
    """Print available scenarios."""
    print("\nAvailable E2E scenarios:")
    print(f"{'ID':<15} {'Name':<30} {'Tags'}")
    print("-" * 65)
    for sid, m in SCENARIO_REGISTRY.items():
        tags = ", ".join(m.tags)
        print(f"{sid:<15} {m.name:<30} {tags}")


async def cli_main() -> int:
    """CLI entry point. Returns exit code."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Run E2E benchmark scenarios",
    )
    parser.add_argument(
        "scenario_id",
        nargs="?",
        help="Scenario ID to run (e.g., E2E-BugFix, E2E-CLI)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available scenarios",
    )
    args = parser.parse_args()

    if args.list:
        list_scenarios()
        return 0

    if not args.scenario_id:
        parser.print_help()
        return 1

    manifest = SCENARIO_REGISTRY.get(args.scenario_id)
    if manifest is None:
        print(f"ERROR: Unknown scenario '{args.scenario_id}'")
        list_scenarios()
        return 1

    # Validate manifest at startup (S3)
    try:
        validate_manifest(manifest)
    except ManifestValidationError as e:
        print(f"ERROR: {e}")
        return 2

    result = await run_scenario(manifest)
    verdict = result.get("verdict", "INFRA_FAIL")

    if verdict == rcb.BenchmarkVerdict.PASS:
        return 0
    elif verdict == rcb.BenchmarkVerdict.INFRA_FAIL:
        return 2
    else:
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(cli_main()))
