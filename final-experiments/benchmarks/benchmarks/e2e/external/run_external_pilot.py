#!/usr/bin/env python3
"""External benchmark pilot runner: SWE-bench + Terminal-Bench via Harbor.

Runs a pilot subset of external benchmarks against specified agents,
aggregates results, and stores artifacts in docs/qa/test-results/.

Harbor CLI (v0.1.44+) is required. Install: pip install harbor
See: https://github.com/laude-institute/harbor

Usage:
    uv run python scripts/e2e/external/run_external_pilot.py \
        --agent codex --suite swebench --model gpt-4o

    uv run python scripts/e2e/external/run_external_pilot.py \
        --agent claude-code --suite terminalbench --parity-runs 3

    uv run python scripts/e2e/external/run_external_pilot.py --help
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
RESULTS_DIR = PROJECT_ROOT / "docs" / "qa" / "test-results"
MANIFEST_DIR = Path(__file__).resolve().parent

# Harbor dataset names (from `harbor datasets list`)
SUITE_CONFIGS = {
    "swebench": {
        "manifest_file": "swebench-pilot-subset.json",
        "wall_time_per_task_s": 600,
        "token_cap_per_task": 50_000,
        "max_tool_calls_per_task": 100,
        "harbor_dataset": "swebench-verified@1.0",
    },
    "terminalbench": {
        "manifest_file": "terminalbench-pilot-subset.json",
        "wall_time_per_task_s": 900,
        "token_cap_per_task": 50_000,
        "max_tool_calls_per_task": 100,
        "harbor_dataset": "terminal-bench@2.0",
    },
}

# Harbor agent names (from `harbor run --help`)
# Valid: oracle, nop, claude-code, cline-cli, terminus, terminus-1, terminus-2,
#        aider, codex, cursor-cli, gemini-cli, goose, mini-swe-agent,
#        swe-agent, opencode, openhands, qwen-coder
AGENT_CONFIGS = {
    "codex": {
        "default_model": "gpt-4o",
        "harbor_agent": "codex",
    },
    "claude-code": {
        "default_model": "claude-sonnet-4-5-20250929",
        "harbor_agent": "claude-code",
    },
}

# Default Harbor executable; override with HARBOR_EXE env var
DEFAULT_HARBOR_EXE = "harbor"


def find_harbor_exe() -> str:
    """Find the Harbor CLI executable."""
    # Check env var first
    harbor_exe = os.environ.get("HARBOR_EXE", "")
    if harbor_exe and (Path(harbor_exe).exists() or shutil.which(harbor_exe)):
        return harbor_exe

    # Check PATH
    if shutil.which("harbor"):
        return "harbor"

    # Check common venv locations on K: drive (Windows)
    venv_candidates = [
        Path(r"K:\tools\harbor-venv\Scripts\harbor.exe"),
        Path(r"K:\tools\harbor-venv\bin\harbor"),
    ]
    for candidate in venv_candidates:
        if candidate.exists():
            return str(candidate)

    return DEFAULT_HARBOR_EXE


def check_prerequisites(harbor_exe: str) -> list[str]:
    """Check that required tools are installed. Returns list of blockers."""
    blockers = []

    # Check Docker
    if not shutil.which("docker"):
        blockers.append("Docker is not installed or not in PATH")
    else:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if result.returncode != 0:
            blockers.append("Docker daemon is not running")

    # Check Harbor CLI
    harbor_path = shutil.which(harbor_exe) or (
        harbor_exe if Path(harbor_exe).exists() else None
    )
    if not harbor_path:
        blockers.append(
            f"Harbor CLI not found at '{harbor_exe}'. "
            "Install with: pip install harbor  "
            "Or set HARBOR_EXE env var to the full path."
        )
    else:
        # Verify it works
        try:
            result = subprocess.run(
                [harbor_exe, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                print(f"  Harbor CLI found: v{version}")
            else:
                blockers.append(
                    f"Harbor CLI at '{harbor_exe}' returned error: "
                    f"{result.stderr.strip()}"
                )
        except (subprocess.TimeoutExpired, OSError) as e:
            blockers.append(f"Harbor CLI at '{harbor_exe}' failed: {e}")

    # Check API keys based on common env vars
    api_key_vars = [
        "OPENROUTER_API_KEY",
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
    ]
    has_key = any(os.environ.get(v) for v in api_key_vars)
    if not has_key:
        blockers.append(
            f"No API key found. Set one of: {', '.join(api_key_vars)}"
        )

    return blockers


def load_manifest(suite: str) -> dict:
    """Load the pilot subset manifest for the given suite."""
    config = SUITE_CONFIGS[suite]
    manifest_path = MANIFEST_DIR / config["manifest_file"]
    if not manifest_path.exists():
        print(f"ERROR: Manifest not found: {manifest_path}")
        sys.exit(1)
    with open(manifest_path, encoding="utf-8") as f:
        return json.load(f)


def run_harbor_task(
    task_id: str,
    suite: str,
    agent: str,
    model: str,
    suite_config: dict,
    harbor_exe: str,
    jobs_dir: Path,
) -> dict:
    """Run a single task via Harbor CLI. Returns result dict.

    Harbor CLI (v0.1.44) command structure:
        harbor run --dataset <name@version> --task-name <id>
            --agent <agent> --model <model> --jobs-dir <path>
            --timeout-multiplier <float> --n-tasks 1
    """
    agent_config = AGENT_CONFIGS[agent]
    harbor_agent = agent_config["harbor_agent"]

    # Build Harbor command
    cmd = [
        harbor_exe, "run",
        "--dataset", suite_config["harbor_dataset"],
        "--task-name", task_id,
        "--agent", harbor_agent,
        "--model", model,
        "--jobs-dir", str(jobs_dir),
        "--n-tasks", "1",
        "--n-concurrent", "1",
    ]

    print(f"  Running: {' '.join(cmd)}")
    start = time.monotonic()

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=suite_config["wall_time_per_task_s"] + 120,  # grace period
            check=False,
        )
        elapsed = time.monotonic() - start

        if result.returncode == 0:
            # Harbor writes results to jobs_dir; try to parse
            task_result = _parse_harbor_job_output(jobs_dir, task_id)
            if task_result is None:
                task_result = {
                    "raw_stdout": result.stdout[:2000] if result.stdout else "",
                }
            task_result["verdict"] = task_result.get("verdict", "PASS")
        else:
            task_result = {
                "verdict": "FAIL",
                "error": result.stderr[:1000] if result.stderr else "non-zero exit",
                "exit_code": result.returncode,
                "raw_stdout": result.stdout[:500] if result.stdout else "",
            }

        task_result["task_id"] = task_id
        task_result["wall_time_s"] = round(elapsed, 1)
        return task_result

    except subprocess.TimeoutExpired:
        return {
            "task_id": task_id,
            "verdict": "INFRA_FAIL",
            "error": "Task timed out",
            "wall_time_s": suite_config["wall_time_per_task_s"],
        }
    except FileNotFoundError:
        return {
            "task_id": task_id,
            "verdict": "INFRA_FAIL",
            "error": f"Harbor CLI not found at '{harbor_exe}'",
            "wall_time_s": 0,
        }


def _parse_harbor_job_output(jobs_dir: Path, task_id: str) -> dict | None:
    """Try to parse Harbor job output from the jobs directory.

    Harbor writes trial results under jobs_dir/<job_name>/trials/.
    Structure varies by version; this is a best-effort parser.
    """
    if not jobs_dir.exists():
        return None

    # Look for the most recent job directory
    job_dirs = sorted(jobs_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
    for job_dir in job_dirs:
        if not job_dir.is_dir():
            continue
        # Look for trial results
        trials_dir = job_dir / "trials"
        if trials_dir.exists():
            for trial_dir in trials_dir.iterdir():
                if not trial_dir.is_dir():
                    continue
                # Check for result.json or similar
                for result_file in ["result.json", "trial.json", "output.json"]:
                    result_path = trial_dir / result_file
                    if result_path.exists():
                        try:
                            with open(result_path, encoding="utf-8") as f:
                                data = json.load(f)
                            # Map Harbor verdict to our verdict system
                            if data.get("resolved", False) or data.get("passed", False):
                                data["verdict"] = "PASS"
                            else:
                                data["verdict"] = "FAIL"
                            return data
                        except (json.JSONDecodeError, OSError):
                            continue
    return None


def aggregate_results(
    task_results: list[dict],
    suite: str,
    agent: str,
    model: str,
    manifest: dict,
    parity_run: int | None = None,
) -> dict:
    """Aggregate per-task results into a summary."""
    passed = sum(1 for r in task_results if r.get("verdict") == "PASS")
    failed = sum(1 for r in task_results if r.get("verdict") == "FAIL")
    infra_fail = sum(1 for r in task_results if r.get("verdict") == "INFRA_FAIL")
    total = len(task_results)

    resolve_rate = passed / total if total > 0 else 0.0
    avg_time = (
        sum(r.get("wall_time_s", 0) for r in task_results) / total
        if total > 0
        else 0
    )

    return {
        "suite": suite,
        "agent": agent,
        "model": model,
        "total_tasks": total,
        "passed": passed,
        "failed": failed,
        "infra_fail": infra_fail,
        "resolve_rate": round(resolve_rate, 4),
        "avg_wall_time_per_task_s": round(avg_time, 1),
        "parity_run": parity_run,
        "timestamp": datetime.now(UTC).isoformat(),
    }


def save_artifacts(
    suite: str,
    agent: str,
    task_results: list[dict],
    summary: dict,
    config_data: dict,
    parity_run: int | None = None,
) -> Path:
    """Save run artifacts to docs/qa/test-results/."""
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    suffix = f"-run{parity_run}" if parity_run is not None else ""
    dir_name = f"{ts}-external-pilot-{suite}-{agent}{suffix}"
    output_dir = RESULTS_DIR / dir_name
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save config
    config_path = output_dir / "config.json"
    config_path.write_text(
        json.dumps(config_data, indent=2, default=str), encoding="utf-8"
    )

    # Save summary JSON
    summary_json_path = output_dir / "summary.json"
    summary_json_path.write_text(
        json.dumps(summary, indent=2, default=str), encoding="utf-8"
    )

    # Save per-task results
    per_task_dir = output_dir / "per-task"
    per_task_dir.mkdir(exist_ok=True)
    for result in task_results:
        task_id = result.get("task_id", "unknown").replace("/", "_")
        task_path = per_task_dir / f"{task_id}.json"
        task_path.write_text(
            json.dumps(result, indent=2, default=str), encoding="utf-8"
        )

    # Save markdown summary
    md_lines = [
        f"# External Pilot Report: {suite} / {agent}",
        f"**Date:** {summary['timestamp']}",
        f"**Model:** {summary['model']}",
        f"**Resolve rate:** {summary['resolve_rate']:.1%} "
        f"({summary['passed']}/{summary['total_tasks']})",
        "",
        "## Results",
        "",
        "| Task ID | Verdict | Wall Time (s) |",
        "|---------|---------|---------------|",
    ]
    for r in task_results:
        md_lines.append(
            f"| {r['task_id']} | {r.get('verdict', 'UNKNOWN')} | "
            f"{r.get('wall_time_s', '-')} |"
        )
    md_lines.extend([
        "",
        "## Summary",
        f"- Passed: {summary['passed']}",
        f"- Failed: {summary['failed']}",
        f"- Infra failures: {summary['infra_fail']}",
        f"- Avg wall time: {summary['avg_wall_time_per_task_s']}s",
    ])

    summary_md_path = output_dir / "summary.md"
    summary_md_path.write_text("\n".join(md_lines), encoding="utf-8")

    return output_dir


def run_pilot(
    agent: str,
    suite: str,
    model: str | None,
    parity_runs: int,
    dry_run: bool = False,
) -> int:
    """Run the full pilot. Returns exit code."""
    suite_config = SUITE_CONFIGS[suite]
    agent_config = AGENT_CONFIGS[agent]
    effective_model = model or agent_config["default_model"]
    harbor_exe = find_harbor_exe()

    print(f"\n{'='*60}")
    print(f"  External Pilot: {suite} / {agent}")
    print(f"  Model: {effective_model}")
    print(f"  Harbor: {harbor_exe}")
    print(f"  Dataset: {suite_config['harbor_dataset']}")
    print(f"  Parity runs: {parity_runs}")
    print(f"{'='*60}\n")

    # Check prerequisites
    blockers = check_prerequisites(harbor_exe)
    if blockers:
        print("BLOCKERS DETECTED — cannot run external pilot:")
        for b in blockers:
            print(f"  - {b}")
        print("\nResolve blockers and retry.")
        print("Run script with --dry-run to skip prerequisites check.")
        if not dry_run:
            return 2

    # Load manifest
    manifest = load_manifest(suite)
    tasks = manifest.get("tasks", [])
    print(f"Loaded {len(tasks)} tasks from manifest\n")

    config_data = {
        "suite": suite,
        "agent": agent,
        "model": effective_model,
        "harbor_dataset": suite_config["harbor_dataset"],
        "subset_manifest": str(MANIFEST_DIR / suite_config["manifest_file"]),
        "budget": {
            "wall_time_per_task_s": suite_config["wall_time_per_task_s"],
            "token_cap_per_task": suite_config["token_cap_per_task"],
            "max_tool_calls_per_task": suite_config["max_tool_calls_per_task"],
        },
        "parity_runs": parity_runs,
        "timestamp": datetime.now(UTC).isoformat(),
    }

    all_summaries = []

    for run_idx in range(parity_runs):
        run_label = f" (run {run_idx + 1}/{parity_runs})" if parity_runs > 1 else ""
        print(f"\n--- Pilot Run{run_label} ---\n")

        # Per-run jobs directory for Harbor output
        jobs_dir = RESULTS_DIR / f"_harbor_jobs_{suite}_{agent}_{run_idx}"
        jobs_dir.mkdir(parents=True, exist_ok=True)

        task_results = []
        for i, task in enumerate(tasks):
            task_id = task["task_id"]
            print(f"[{i + 1}/{len(tasks)}] Task: {task_id}")

            if dry_run:
                # Simulate result for dry run
                task_results.append({
                    "task_id": task_id,
                    "verdict": "INFRA_FAIL",
                    "error": "dry-run mode — Harbor not invoked",
                    "wall_time_s": 0,
                })
            else:
                result = run_harbor_task(
                    task_id, suite, agent, effective_model,
                    suite_config, harbor_exe, jobs_dir,
                )
                task_results.append(result)
                verdict = result.get("verdict", "UNKNOWN")
                print(f"  -> {verdict} ({result.get('wall_time_s', 0)}s)")

        parity_idx = run_idx if parity_runs > 1 else None
        summary = aggregate_results(
            task_results, suite, agent, effective_model, manifest, parity_idx,
        )
        all_summaries.append(summary)

        output_dir = save_artifacts(
            suite, agent, task_results, summary, config_data, parity_idx,
        )
        print(f"\nArtifacts saved: {output_dir}")
        print(
            f"Resolve rate: {summary['resolve_rate']:.1%} "
            f"({summary['passed']}/{summary['total_tasks']})"
        )

    # Parity variance
    if parity_runs > 1 and all_summaries:
        rates = [s["resolve_rate"] for s in all_summaries]
        mean_rate = sum(rates) / len(rates)
        variance = sum((r - mean_rate) ** 2 for r in rates) / len(rates)
        std_dev = variance ** 0.5
        print(f"\n--- Parity Analysis ---")
        print(f"Resolve rates: {rates}")
        print(f"Mean: {mean_rate:.4f}, Std Dev: {std_dev:.4f}")

    return 0


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Run external benchmark pilot (SWE-bench / Terminal-Bench)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  %(prog)s --agent codex --suite swebench\n"
            "  %(prog)s --agent claude-code --suite terminalbench --parity-runs 3\n"
            "  %(prog)s --agent codex --suite swebench --dry-run\n"
        ),
    )
    parser.add_argument(
        "--agent",
        required=True,
        choices=list(AGENT_CONFIGS.keys()),
        help="Agent to benchmark (codex or claude-code)",
    )
    parser.add_argument(
        "--suite",
        required=True,
        choices=list(SUITE_CONFIGS.keys()),
        help="Benchmark suite to run (swebench or terminalbench)",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Model ID to use (defaults to agent's default model)",
    )
    parser.add_argument(
        "--parity-runs",
        type=int,
        default=1,
        help="Number of repeat runs for variance estimation (default: 1)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate setup without running tasks (skips Harbor invocation)",
    )
    args = parser.parse_args()

    return run_pilot(
        agent=args.agent,
        suite=args.suite,
        model=args.model,
        parity_runs=args.parity_runs,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    sys.exit(main())
