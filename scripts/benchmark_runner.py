#!/usr/bin/env python3
"""Unified benchmark runner with agent adapter selection.

Runs benchmark lanes (B6-B14) against any agent (AutoCode, Codex, Claude Code)
with identical prompts, budgets, and grading for valid parity comparisons.

Usage:
    # Run AutoCode on B6
    uv run python scripts/benchmark_runner.py --agent autocode --lane B6

    # Run Codex on B7 for parity
    uv run python scripts/benchmark_runner.py --agent codex --lane B7

    # Run all agents on B7
    uv run python scripts/benchmark_runner.py --agent all --lane B7

    # List available lanes
    uv run python scripts/benchmark_runner.py --list-lanes

Per Entry 530: only local_free and subscription providers allowed.
paid_metered is FORBIDDEN by policy.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.adapters.autocode_adapter import AutoCodeAdapter  # noqa: E402
from scripts.adapters.base import (  # noqa: E402
    AgentAdapter,
    AgentResult,
    BenchmarkTask,
    BudgetProfile,
    compute_manifest_hash,
    load_manifest,
)
from scripts.adapters.claude_adapter import ClaudeCodeAdapter  # noqa: E402
from scripts.adapters.codex_adapter import CodexAdapter  # noqa: E402

# --- Version ---
HARNESS_VERSION = "1.0.0"

# --- Paths ---
MANIFEST_DIR = PROJECT_ROOT / "scripts" / "e2e" / "external"
RESULTS_DIR = PROJECT_ROOT / "docs" / "qa" / "test-results"
SANDBOXES_DIR = PROJECT_ROOT / "sandboxes"

# --- Lane Configs ---
LANE_CONFIGS: dict[str, dict] = {
    "B6": {
        "name": "React Calculator",
        "manifest": None,  # B6 uses its own runner
        "budget": BudgetProfile(wall_time_s=600, token_cap=50_000, max_tool_calls=50),
        "runner": "calculator",
        "description": "Build a React calculator app from scratch",
    },
    "B7": {
        "name": "SWE-bench Verified",
        "manifest": "swebench-pilot-subset.json",
        "budget": BudgetProfile(
            wall_time_s=3600, token_cap=50_000, max_tool_calls=100,
        ),
        "runner": "swebench",
        "description": "Fix Python bugs from SWE-bench Verified (25 tasks)",
    },
    "B8": {
        "name": "SWE-bench Bash-Only",
        "manifest": "swebench-pilot-subset.json",
        "budget": BudgetProfile(
            wall_time_s=600, token_cap=50_000, max_tool_calls=100,
        ),
        "runner": "swebench",
        "tool_restriction": "bash-only",
        "description": "SWE-bench with bash tools only (control lane)",
    },
    "B9": {
        "name": "Terminal-Bench",
        "manifest": "terminalbench-pilot-subset.json",
        "budget": BudgetProfile(
            wall_time_s=900, token_cap=50_000, max_tool_calls=100,
        ),
        "runner": "terminalbench",
        "description": "Terminal workflow tasks (10 tasks)",
    },
    "B10": {
        "name": "SWE-bench Multilingual",
        "manifest": "b10-multilingual-subset.json",
        "budget": BudgetProfile(
            wall_time_s=1200, token_cap=50_000, max_tool_calls=100,
        ),
        "runner": "swebench",
        "description": "Multilingual bug fixes (36 tasks, 9 languages)",
    },
    "B11": {
        "name": "BaxBench",
        "manifest": "baxbench-pilot-subset.json",
        "budget": BudgetProfile(
            wall_time_s=600, token_cap=50_000, max_tool_calls=100,
        ),
        "runner": "swebench",
        "description": "Backend/security tasks (10-15 tasks)",
    },
    "B12-PROXY": {
        "name": "SWE-Lancer Equivalent (PROXY)",
        "manifest": "b12-proxy-subset.json",
        "budget": BudgetProfile(
            wall_time_s=900, token_cap=50_000, max_tool_calls=100,
        ),
        "runner": "swebench",
        "comparison_validity": "proxy-only",
        "description": "Freelance-style SWE tasks (proxy, no parity claims)",
    },
    "B13-PROXY": {
        "name": "CodeClash Equivalent (PROXY)",
        "manifest": "b13-proxy-subset.json",
        "budget": BudgetProfile(
            wall_time_s=600, token_cap=50_000, max_tool_calls=100,
        ),
        "runner": "competitive",
        "comparison_validity": "proxy-only",
        "description": "Competitive coding tasks (proxy, no parity claims)",
    },
    "B14": {
        "name": "LiveCodeBench",
        "manifest": "livecodebench-pilot-subset.json",
        "budget": BudgetProfile(
            wall_time_s=600, token_cap=50_000, max_tool_calls=100,
        ),
        "runner": "competitive",
        "description": "LeetCode-style problems (15-20 tasks)",
    },
}

# --- Agent Registry ---
AGENT_REGISTRY: dict[str, type] = {
    "autocode": AutoCodeAdapter,
    "codex": CodexAdapter,
    "claude-code": ClaudeCodeAdapter,
}


def get_adapter(agent_name: str, model: str = "") -> AgentAdapter:
    """Create an agent adapter by name."""
    cls = AGENT_REGISTRY.get(agent_name)
    if cls is None:
        raise ValueError(
            f"Unknown agent: {agent_name}. "
            f"Available: {', '.join(AGENT_REGISTRY)}"
        )
    return cls(model=model)


def create_task_sandbox(lane: str, task_id: str) -> Path:
    """Create a sandbox directory for a single task."""
    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    sandbox = SANDBOXES_DIR / f"bench_{lane}_{task_id}_{ts}"
    sandbox.mkdir(parents=True, exist_ok=True)
    return sandbox


# --- Run Contract (Reproducibility) ---

def build_run_contract(
    agent: AgentAdapter,
    lane: str,
    manifest_path: Path | None,
    budget: BudgetProfile,
    command_trace: str,
) -> dict:
    """Build the reproducibility contract for a run."""
    return {
        "harness_version": HARNESS_VERSION,
        "agent": agent.name,
        "agent_version": agent.version,
        "model": agent.model,
        "provider_mode": agent.provider_mode,
        "lane": lane,
        "manifest_hash": (
            compute_manifest_hash(manifest_path)
            if manifest_path and manifest_path.exists()
            else "none"
        ),
        "budget_profile": {
            "wall_time_s": budget.wall_time_s,
            "token_cap": budget.token_cap,
            "max_tool_calls": budget.max_tool_calls,
        },
        "budget_profile_id": budget.profile_id,
        "command_trace": command_trace,
        "timestamp": datetime.now(UTC).isoformat(),
        "comparison_validity": (
            LANE_CONFIGS.get(lane, {}).get("comparison_validity", "parity-valid")
        ),
    }


# --- Task Runner ---

async def run_lane(
    agent: AgentAdapter,
    lane: str,
    tasks: list[BenchmarkTask],
    budget: BudgetProfile,
    manifest_path: Path | None,
) -> dict:
    """Run all tasks in a lane sequentially and return aggregated results."""
    results: list[dict] = []
    resolved_count = 0
    total_time = 0.0
    infra_fails = 0

    print(f"\n{'=' * 60}")
    print(f"Lane: {lane} | Agent: {agent.name} | Model: {agent.model}")
    print(f"Tasks: {len(tasks)} | Budget: {budget.profile_id}")
    print(f"{'=' * 60}")

    for i, task in enumerate(tasks, 1):
        print(f"\n--- Task {i}/{len(tasks)}: {task.task_id} ---")
        print(f"  Description: {task.description[:80]}")

        sandbox = create_task_sandbox(lane, task.task_id)
        print(f"  Sandbox: {sandbox}")

        # Run setup commands if any
        import subprocess
        setup_ok = True
        for cmd in task.setup_commands:
            print(f"  Setup: {cmd[:80]}...")
            try:
                proc = subprocess.run(
                    cmd, shell=True, cwd=str(sandbox),
                    capture_output=True, text=True, timeout=300,
                )
                if proc.returncode != 0:
                    print(f"  Setup warning (rc={proc.returncode}): {proc.stderr[:200]}")
            except Exception as e:
                print(f"  Setup failed: {e}")
                setup_ok = False

        # Apply test_patch if present (SWE-bench workflow)
        test_patch = task.extra.get("test_patch", "")
        if test_patch and setup_ok:
            repo_name = task.extra.get("repo_name", "")
            patch_dir = sandbox / repo_name if repo_name else sandbox
            if patch_dir.exists():
                patch_file = sandbox / "test_patch.diff"
                patch_file.write_text(test_patch, encoding="utf-8")
                # Use forward slashes for git on Windows
                patch_path_str = str(patch_file).replace("\\", "/")
                try:
                    proc = subprocess.run(
                        f'git apply --allow-empty --ignore-whitespace "{patch_path_str}"',
                        shell=True, cwd=str(patch_dir),
                        capture_output=True, text=True, timeout=30,
                    )
                    if proc.returncode == 0:
                        print("  Test patch applied successfully")
                    else:
                        print(f"  Test patch warning: {proc.stderr[:200]}")
                except Exception as e:
                    print(f"  Test patch failed: {e}")

        if not setup_ok:
            result = AgentResult(
                task_id=task.task_id,
                resolved=False,
                error="Setup failed",
            )
        else:
            result = await agent.solve_task(task, sandbox, budget)

        status = "RESOLVED" if result.resolved else "FAILED"
        if result.error:
            status = f"ERROR: {result.error[:50]}"
            infra_fails += 1

        print(f"  Result: {status} ({result.wall_time_s}s)")

        if result.resolved:
            resolved_count += 1
        total_time += result.wall_time_s

        results.append({
            "task_id": result.task_id,
            "resolved": result.resolved,
            "score": result.score,
            "wall_time_s": result.wall_time_s,
            "tool_calls": result.tool_calls,
            "tokens_in": result.tokens_in,
            "tokens_out": result.tokens_out,
            "error": result.error,
        })

    # Aggregate
    resolve_rate = resolved_count / len(tasks) if tasks else 0
    infra_fail_rate = infra_fails / len(tasks) if tasks else 0

    aggregate = {
        "total_tasks": len(tasks),
        "resolved": resolved_count,
        "resolve_rate": round(resolve_rate, 3),
        "infra_fails": infra_fails,
        "infra_fail_rate": round(infra_fail_rate, 3),
        "total_wall_time_s": round(total_time, 1),
        "avg_wall_time_s": round(total_time / len(tasks), 1) if tasks else 0,
    }

    print(f"\n{'=' * 60}")
    print(f"LANE {lane} COMPLETE")
    print(
        f"  Resolved: {resolved_count}/{len(tasks)} "
        f"({resolve_rate:.1%})"
    )
    print(f"  Infra fails: {infra_fails}")
    print(f"  Total time: {total_time:.1f}s")
    print(f"{'=' * 60}")

    return {
        "lane": lane,
        "lane_name": LANE_CONFIGS.get(lane, {}).get("name", lane),
        "agent": agent.name,
        "model": agent.model,
        "provider_mode": agent.provider_mode,
        "aggregate": aggregate,
        "results": results,
    }


# --- Report Generation ---

def save_run_report(
    run_data: dict,
    contract: dict,
) -> Path:
    """Save run results as JSON artifact."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    lane = run_data["lane"]
    agent = run_data["agent"]

    report = {
        "contract": contract,
        **run_data,
    }

    filename = f"{ts}-{lane}-{agent}.json"
    report_path = RESULTS_DIR / filename
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"\nArtifact saved: {report_path}")
    return report_path


def print_comparison_table(reports: list[dict]) -> None:
    """Print a comparison table across agents for the same lane."""
    if not reports:
        return

    lane = reports[0].get("lane", "?")
    print(f"\n{'=' * 70}")
    print(f"PARITY COMPARISON — Lane {lane}")
    print(f"{'=' * 70}")

    # Check parity validity
    harness_versions = {r["contract"]["harness_version"] for r in reports}
    manifest_hashes = {r["contract"]["manifest_hash"] for r in reports}
    budget_ids = {r["contract"]["budget_profile_id"] for r in reports}

    parity_valid = (
        len(harness_versions) == 1
        and len(manifest_hashes) == 1
        and len(budget_ids) == 1
    )

    validity = "parity-valid" if parity_valid else "INVALID"
    print(f"  Comparison validity: {validity}")
    print(f"  Harness: {harness_versions}")
    print(f"  Manifest: {manifest_hashes}")
    print(f"  Budget: {budget_ids}")
    print()

    # Table
    cols = ["Agent", "Model", "Provider", "Resolved", "Rate", "Time"]
    header = (
        f"| {cols[0]:<15} | {cols[1]:<35} | {cols[2]:<12} "
        f"| {cols[3]:<10} | {cols[4]:<8} | {cols[5]:<8} |"
    )
    separator = (
        f"|{'-' * 17}|{'-' * 37}|{'-' * 14}"
        f"|{'-' * 12}|{'-' * 10}|{'-' * 10}|"
    )
    print(header)
    print(separator)

    for r in reports:
        agg = r.get("aggregate", {})
        print(
            f"| {r['agent']:<15} "
            f"| {r['model']:<35} "
            f"| {r['provider_mode']:<12} "
            f"| {agg.get('resolved', 0):>3}/{agg.get('total_tasks', 0):<5} "
            f"| {agg.get('resolve_rate', 0):>6.1%} "
            f"| {agg.get('total_wall_time_s', 0):>6.1f}s "
            f"|"
        )

    print(f"\ncomparison_validity: {validity}")


# --- B6 Delegation ---

async def run_b6(agent_name: str, strict: bool) -> dict:
    """Delegate B6 to the existing calculator benchmark runner."""
    if agent_name != "autocode":
        print(
            f"B6 (React Calculator) only supports autocode agent, "
            f"not {agent_name}"
        )
        return {"lane": "B6", "error": "B6 only supports autocode"}

    print("\nDelegating B6 to scripts/run_calculator_benchmark.py...")
    import subprocess
    cmd = [
        sys.executable, "-m", "scripts.run_calculator_benchmark",
        "--runs", "1",
    ]
    if strict:
        cmd.append("--strict")

    proc = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    return {
        "lane": "B6",
        "agent": "autocode",
        "returncode": proc.returncode,
    }


# --- Main ---

async def main() -> int:
    parser = argparse.ArgumentParser(
        description="Unified benchmark runner with agent adapter selection",
    )
    parser.add_argument(
        "--agent",
        choices=list(AGENT_REGISTRY) + ["all"],
        default="autocode",
        help="Agent to run (default: autocode)",
    )
    parser.add_argument(
        "--lane",
        choices=list(LANE_CONFIGS),
        help="Benchmark lane to run",
    )
    parser.add_argument(
        "--model",
        default="",
        help="Override model for the agent",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Use strict mode (higher thresholds)",
    )
    parser.add_argument(
        "--list-lanes",
        action="store_true",
        help="List available benchmark lanes",
    )
    parser.add_argument(
        "--max-tasks",
        type=int,
        default=0,
        help="Limit number of tasks (0 = all)",
    )

    args = parser.parse_args()

    if args.list_lanes:
        print("\nAvailable benchmark lanes:")
        print(f"{'Lane':<12} {'Name':<30} {'Tasks':<10} {'Description'}")
        print("-" * 80)
        for lane_id, cfg in LANE_CONFIGS.items():
            manifest = cfg.get("manifest")
            task_count = "N/A"
            if manifest:
                mpath = MANIFEST_DIR / manifest
                if mpath.exists():
                    _, tasks = load_manifest(mpath)
                    task_count = str(len(tasks))
                else:
                    task_count = "NO FILE"
            print(
                f"{lane_id:<12} {cfg['name']:<30} "
                f"{task_count:<10} {cfg.get('description', '')}"
            )
        return 0

    if not args.lane:
        parser.error("--lane is required (use --list-lanes to see options)")

    lane = args.lane
    lane_cfg = LANE_CONFIGS[lane]

    # B6 delegates to its own runner
    if lane == "B6":
        await run_b6(args.agent, args.strict)
        return 0

    # Load manifest
    manifest_file = lane_cfg.get("manifest")
    if not manifest_file:
        print(f"Lane {lane} has no manifest configured")
        return 1

    manifest_path = MANIFEST_DIR / manifest_file
    if not manifest_path.exists():
        print(f"Manifest not found: {manifest_path}")
        print(
            "Create the manifest first, then re-run. "
            "See benchmarks/EVALUATION.md for manifest schema."
        )
        return 1

    meta, tasks = load_manifest(manifest_path)
    if args.max_tasks > 0:
        tasks = tasks[: args.max_tasks]

    budget = lane_cfg["budget"]

    # Determine agents to run
    agent_names = (
        list(AGENT_REGISTRY) if args.agent == "all" else [args.agent]
    )

    reports = []
    command_trace = " ".join(sys.argv)

    for agent_name in agent_names:
        adapter = get_adapter(agent_name, model=args.model)

        # Validate provider policy (Entry 530)
        if adapter.provider_mode == "paid_metered":
            print(
                f"BLOCKED: Agent {agent_name} uses paid_metered provider. "
                f"This is forbidden by policy (Entry 530)."
            )
            continue

        contract = build_run_contract(
            adapter, lane, manifest_path, budget, command_trace,
        )

        run_data = await run_lane(adapter, lane, tasks, budget, manifest_path)
        run_data["contract"] = contract

        save_run_report(run_data, contract)
        reports.append(run_data)

    # Print comparison if multiple agents
    if len(reports) > 1:
        print_comparison_table(reports)

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
