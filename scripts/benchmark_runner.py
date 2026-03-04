#!/usr/bin/env python3
"""Unified benchmark runner with agent adapter selection.

Runs benchmark lanes (B6-B14) against any agent (AutoCode, Codex, Claude Code)
with identical budgets and grading for valid parity comparisons.

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
import os
import re
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

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
from scripts.docker_helpers import (  # noqa: E402
    docker_available,
    docker_exec,
    fix_permissions,
    get_image_digest,
    install_build_deps,
    make_container_name,
    start_container,
    stop_and_remove,
)

# --- Version ---
HARNESS_VERSION = "1.0.0"

# --- Paths ---
MANIFEST_DIR = PROJECT_ROOT / "scripts" / "e2e" / "external"
RESULTS_DIR = PROJECT_ROOT / "docs" / "qa" / "test-results"
SANDBOXES_DIR = PROJECT_ROOT / "sandboxes"
PROGRESS_DIR = PROJECT_ROOT / "sandboxes" / "progress"


# --- Progress Tracking (Resumability) ---

def _progress_path(lane: str, agent_name: str) -> Path:
    """Return path to the progress file for a lane+agent combination."""
    PROGRESS_DIR.mkdir(parents=True, exist_ok=True)
    return PROGRESS_DIR / f"{lane}_{agent_name}_progress.json"


def _load_progress(lane: str, agent_name: str) -> dict:
    """Load existing progress for a lane+agent. Returns empty dict if none."""
    path = _progress_path(lane, agent_name)
    if path.exists():
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_progress(
    lane: str,
    agent_name: str,
    completed_results: list[dict],
    image_digests: dict[str, str],
) -> None:
    """Save progress after each task completes.

    Stores completed task results so a resumed run can skip them.
    """
    path = _progress_path(lane, agent_name)
    data = {
        "lane": lane,
        "agent": agent_name,
        "completed_task_ids": [r["task_id"] for r in completed_results],
        "results": completed_results,
        "image_digests": image_digests,
        "last_updated": datetime.now(UTC).isoformat(),
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _clear_progress(lane: str, agent_name: str) -> None:
    """Remove progress file after a lane completes successfully."""
    path = _progress_path(lane, agent_name)
    if path.exists():
        path.unlink()


def _extract_patch_files(patch_text: str) -> list[str]:
    """Extract file paths from a unified diff patch.

    Parses '--- a/path' and '+++ b/path' lines to find which files
    the test patch modifies. Returns relative paths.
    """
    files: set[str] = set()
    for match in re.finditer(
        r"^(?:\+\+\+|---) [ab]/(.+)$", patch_text, re.MULTILINE,
    ):
        path = match.group(1).strip()
        if path and path != "/dev/null":
            files.add(path)
    return sorted(files)


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
            wall_time_s=7200, token_cap=50_000, max_tool_calls=100,
        ),
        "runner": "swebench",
        "description": "Fix Python bugs from SWE-bench Verified (24 tasks)",
    },
    "B8": {
        "name": "SWE-bench Bash-Only",
        "manifest": "swebench-pilot-subset.json",
        "budget": BudgetProfile(
            wall_time_s=7200, token_cap=50_000, max_tool_calls=100,
        ),
        "runner": "swebench",
        "tool_restriction": "bash-only",
        "description": "SWE-bench with bash tools only (control lane)",
    },
    "B9-PROXY": {
        "name": "Terminal-Bench Equivalent",
        "manifest": "b9-proxy-subset.json",
        "budget": BudgetProfile(
            wall_time_s=7200, token_cap=50_000, max_tool_calls=100,
        ),
        "runner": "swebench",
        "comparison_validity": "proxy-only",
        "description": "Terminal workflow proxy tasks (10 tasks)",
    },
    "B10-PROXY": {
        "name": "Multilingual Equivalent",
        "manifest": "b10-proxy-subset.json",
        "budget": BudgetProfile(
            wall_time_s=7200, token_cap=50_000, max_tool_calls=100,
        ),
        "runner": "swebench",
        "comparison_validity": "proxy-only",
        "description": "Multilingual bug fix proxy tasks (10 Python tasks)",
    },
    "B11": {
        "name": "BaxBench",
        "manifest": "baxbench-pilot-subset.json",
        "budget": BudgetProfile(
            wall_time_s=7200, token_cap=50_000, max_tool_calls=100,
        ),
        "runner": "swebench",
        "description": "Backend/security tasks (10-15 tasks)",
    },
    "B12-PROXY": {
        "name": "SWE-Lancer Equivalent (PROXY)",
        "manifest": "b12-proxy-subset.json",
        "budget": BudgetProfile(
            wall_time_s=7200, token_cap=50_000, max_tool_calls=100,
        ),
        "runner": "swebench",
        "comparison_validity": "proxy-only",
        "description": "Freelance-style SWE tasks (proxy, no parity claims)",
    },
    "B13-PROXY": {
        "name": "CodeClash Equivalent (PROXY)",
        "manifest": "b13-proxy-subset.json",
        "budget": BudgetProfile(
            wall_time_s=7200, token_cap=50_000, max_tool_calls=100,
        ),
        "runner": "competitive",
        "comparison_validity": "proxy-only",
        "description": "Competitive coding tasks (proxy, no parity claims)",
    },
    "B14-PROXY": {
        "name": "LiveCodeBench Equivalent (PROXY)",
        "manifest": "b14-proxy-subset.json",
        "budget": BudgetProfile(
            wall_time_s=7200, token_cap=50_000, max_tool_calls=100,
        ),
        "runner": "competitive",
        "comparison_validity": "proxy-only",
        "description": "LeetCode-style problems (proxy, no parity claims)",
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


# --- NOT_EXECUTABLE Validation ---

def validate_lane_executable(
    lane: str,
    config: dict,
    meta: dict[str, Any],
    tasks: list[BenchmarkTask],
) -> tuple[bool, str]:
    """Check if a lane has enough manifest metadata to actually execute.

    Returns (is_executable, reason).  When is_executable is False the
    caller should skip the lane and record NOT_EXECUTABLE.
    """
    runner = config.get("runner", "")

    if runner == "calculator":
        return True, ""

    if runner == "swebench":
        # Need at least one task with setup + grading + runtime
        for t in tasks:
            has_setup = bool(t.setup_commands)
            has_grading = bool(t.grading_command)
            has_runtime = bool(
                t.extra.get("python_version")
                or t.extra.get("docker_image")
            )
            if has_setup and has_grading and has_runtime:
                return True, ""
        return False, (
            f"No task in {lane} has setup_commands + grading_command "
            f"+ python_version/docker_image. Manifest is skeletal."
        )

    if runner == "terminalbench":
        # Need official dataset linkage or per-task grading
        has_harbor = bool(
            meta.get("harbor_dataset") or meta.get("verifier_kind")
        )
        if has_harbor:
            return True, ""
        for t in tasks:
            if t.grading_command:
                return True, ""
        return False, (
            f"{lane} manifest missing harbor_dataset/verifier_kind "
            f"in _meta and no task has grading_command."
        )

    if runner == "competitive":
        # Need fixture_dir + grading_command on at least one task
        for t in tasks:
            has_fixture = bool(t.extra.get("fixture_dir"))
            has_grading = bool(t.grading_command)
            if has_fixture and has_grading:
                return True, ""
        return False, (
            f"No task in {lane} has fixture_dir + grading_command. "
            f"Competitive runner requires fixture directories."
        )

    # Unknown runner — assume executable (will fail at runtime)
    return True, ""


def create_task_sandbox(lane: str, task_id: str) -> Path:
    """Create a sandbox directory for a single task."""
    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    sandbox = SANDBOXES_DIR / f"bench_{lane}_{task_id}_{ts}"
    sandbox.mkdir(parents=True, exist_ok=True)
    return sandbox


# --- Run Contract (Reproducibility) ---

def _get_harness_commit_sha() -> str:
    """Get the current git commit SHA for reproducibility."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout.strip() if result.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def build_run_contract(
    agent: AgentAdapter,
    lane: str,
    manifest_path: Path | None,
    budget: BudgetProfile,
    command_trace: str,
    image_digests: dict[str, str] | None = None,
) -> dict:
    """Build the reproducibility contract for a run."""
    return {
        "harness_version": HARNESS_VERSION,
        "harness_commit_sha": _get_harness_commit_sha(),
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
        "seed": None,  # deterministic, no randomness
        "image_digests": image_digests or {},
    }


# --- Competitive Task Runner ---

async def _run_competitive_task(
    agent: AgentAdapter,
    task: BenchmarkTask,
    sandbox: Path,
    budget: BudgetProfile,
) -> AgentResult:
    """Run a competitive coding task using fixture files.

    Flow: copy fixture → agent edits solution file → grade with grader.py
    """
    fixture_dir_rel = task.extra.get("fixture_dir", "")
    if not fixture_dir_rel:
        return AgentResult(
            task_id=task.task_id,
            resolved=False,
            error="No fixture_dir in task manifest",
        )

    fixture_dir = MANIFEST_DIR / fixture_dir_rel
    if not fixture_dir.exists():
        return AgentResult(
            task_id=task.task_id,
            resolved=False,
            error=f"Fixture dir not found: {fixture_dir}",
        )

    # Copy fixture contents to sandbox
    for item in fixture_dir.iterdir():
        dest = sandbox / item.name
        if item.is_dir():
            shutil.copytree(item, dest)
        else:
            shutil.copy2(item, dest)
    print(f"  Fixture copied from {fixture_dir}")

    # Read prompt.md for the problem description
    prompt_file = sandbox / "prompt.md"
    problem_prompt = ""
    if prompt_file.exists():
        problem_prompt = prompt_file.read_text(encoding="utf-8")

    # Build a task with competitive-specific metadata
    entry_file = task.extra.get("entry_file", "solution.py")
    grading_cmd = task.grading_command or "python grader.py"

    # Override task fields for the agent
    competitive_task = BenchmarkTask(
        task_id=task.task_id,
        description=(
            f"{problem_prompt}\n\n"
            f"Edit ONLY the file `{entry_file}` to solve this problem. "
            f"Do NOT modify test files."
        ),
        repo="",
        difficulty=task.difficulty,
        language=task.language or "python",
        category=task.category,
        setup_commands=[],
        grading_command=grading_cmd,
        extra={
            **task.extra,
            "_sandbox_dir": str(sandbox),
            "_entry_file": entry_file,
        },
    )

    result = await agent.solve_task(competitive_task, sandbox, budget)

    # Grade: run grading command in sandbox
    if not result.error:
        try:
            proc = subprocess.run(
                grading_cmd,
                shell=True,
                cwd=str(sandbox),
                capture_output=True,
                text=True,
                timeout=120,
                executable="/bin/bash",
            )
            grading_passed = proc.returncode == 0
            if grading_passed:
                result = AgentResult(
                    task_id=result.task_id,
                    resolved=True,
                    score=1.0,
                    wall_time_s=result.wall_time_s,
                    tool_calls=result.tool_calls,
                    tokens_in=result.tokens_in,
                    tokens_out=result.tokens_out,
                    artifacts={
                        **(result.artifacts or {}),
                        "grading_stdout": proc.stdout[-2000:],
                    },
                )
            else:
                result = AgentResult(
                    task_id=result.task_id,
                    resolved=False,
                    score=0.0,
                    wall_time_s=result.wall_time_s,
                    tool_calls=result.tool_calls,
                    tokens_in=result.tokens_in,
                    tokens_out=result.tokens_out,
                    artifacts={
                        **(result.artifacts or {}),
                        "grading_stdout": proc.stdout[-2000:],
                        "grading_stderr": proc.stderr[-1000:],
                    },
                )
        except Exception as e:
            result = AgentResult(
                task_id=result.task_id,
                resolved=False,
                error=f"Grading failed: {e}",
                wall_time_s=result.wall_time_s,
                tool_calls=result.tool_calls,
            )

    return result


# --- Task Runner ---

async def run_lane(
    agent: AgentAdapter,
    lane: str,
    tasks: list[BenchmarkTask],
    budget: BudgetProfile,
    manifest_path: Path | None,
    *,
    resume: bool = False,
) -> dict:
    """Run all tasks in a lane sequentially and return aggregated results."""
    results: list[dict] = []
    resolved_count = 0
    total_time = 0.0
    infra_fails = 0
    image_digests: dict[str, str] = {}  # python_version -> digest

    # Resume: load previously completed tasks
    skipped_ids: set[str] = set()
    if resume:
        progress = _load_progress(lane, agent.name)
        prev_results = progress.get("results", [])
        prev_ids = set(progress.get("completed_task_ids", []))
        if prev_ids:
            # Restore previous results
            results.extend(prev_results)
            for r in prev_results:
                if r.get("resolved"):
                    resolved_count += 1
                total_time += r.get("wall_time_s", 0.0)
                if r.get("error"):
                    infra_fails += 1
            skipped_ids = prev_ids
            # Restore image digests
            image_digests.update(progress.get("image_digests", {}))
            print(
                f"\n[RESUME] Loaded {len(prev_ids)} completed tasks "
                f"from progress file"
            )

    print(f"\n{'=' * 60}")
    print(f"Lane: {lane} | Agent: {agent.name} | Model: {agent.model}")
    remaining = len(tasks) - len(skipped_ids)
    print(
        f"Tasks: {len(tasks)} total, {remaining} remaining "
        f"| Budget: {budget.profile_id}"
    )
    print(f"{'=' * 60}")

    for i, task in enumerate(tasks, 1):
        if task.task_id in skipped_ids:
            print(f"\n--- Task {i}/{len(tasks)}: {task.task_id} [SKIPPED — already completed] ---")
            continue
        print(f"\n--- Task {i}/{len(tasks)}: {task.task_id} ---")
        print(f"  Description: {task.description[:80]}")

        sandbox = create_task_sandbox(lane, task.task_id)
        print(f"  Sandbox: {sandbox}")

        # Competitive runner: copy fixture dir, run on host
        lane_runner = LANE_CONFIGS.get(lane, {}).get("runner", "")
        if lane_runner == "competitive":
            result = await _run_competitive_task(
                agent, task, sandbox, budget,
            )
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
                "artifacts": dict(result.artifacts or {}),
            })
            _save_progress(lane, agent.name, results, image_digests)
            continue

        # Copy fixture directory if present (B11/B12 fixture-based tasks)
        fixture_dir_rel = task.extra.get("fixture_dir", "")
        if fixture_dir_rel:
            fixture_dir = MANIFEST_DIR / fixture_dir_rel
            if fixture_dir.exists():
                for item in fixture_dir.iterdir():
                    dest = sandbox / item.name
                    if item.is_dir():
                        shutil.copytree(item, dest)
                    else:
                        shutil.copy2(item, dest)
                print(f"  Fixture copied from {fixture_dir}")
            else:
                print(f"  WARNING: fixture_dir not found: {fixture_dir}")

        # Determine if this task needs Docker isolation
        python_version = task.extra.get("python_version", "")
        use_docker = bool(python_version)
        container_name = ""

        if use_docker and not docker_available():
            print("  Docker not available — falling back to host")
            use_docker = False

        if use_docker:
            container_name = make_container_name(task.task_id, lane)
            print(
                f"  Docker: python:{python_version}-slim "
                f"({container_name})"
            )

        # Run setup commands
        setup_ok = True
        # Ensure venv bin is on PATH so pip/python resolve (host path)
        setup_env = os.environ.copy()
        venv_bin = str(PROJECT_ROOT / ".venv" / "bin")
        if venv_bin not in setup_env.get("PATH", ""):
            setup_env["PATH"] = f"{venv_bin}:{setup_env.get('PATH', '')}"

        # Setup log collects full output for diagnostics
        setup_log_parts: list[str] = []

        try:
            if use_docker:
                # --- Docker path: setup inside container ---
                proc = start_container(
                    container_name, python_version, str(sandbox),
                )
                if proc.returncode != 0:
                    setup_log_parts.append(
                        f"[container-start] FAILED rc={proc.returncode}\n"
                        f"stdout: {proc.stdout}\nstderr: {proc.stderr}"
                    )
                    print(
                        f"  Container start FAILED: "
                        f"{proc.stderr[:200]}"
                    )
                    setup_ok = False
                else:
                    # Collect image digest for reproducibility
                    if python_version not in image_digests:
                        image_digests[python_version] = (
                            get_image_digest(python_version)
                        )
                    # Install build deps (gcc, git, etc.)
                    try:
                        dep_proc = install_build_deps(container_name)
                        setup_log_parts.append(
                            f"[build-deps] rc={dep_proc.returncode}\n"
                            f"stdout: {dep_proc.stdout}\n"
                            f"stderr: {dep_proc.stderr}"
                        )
                        if dep_proc.returncode != 0:
                            print(
                                f"  Build deps FAILED: "
                                f"{dep_proc.stderr[:200]}"
                            )
                            setup_ok = False
                    except Exception as e:
                        setup_log_parts.append(
                            f"[build-deps] EXCEPTION: {e}"
                        )
                        print(f"  Build deps failed: {e}")
                        setup_ok = False

                # Install per-task extra deps (manifest-driven)
                if setup_ok:
                    extra_apt = task.extra.get("extra_apt_deps", [])
                    if extra_apt:
                        apt_cmd = (
                            "apt-get install -y -qq "
                            + " ".join(extra_apt)
                        )
                        try:
                            dep_proc = docker_exec(
                                container_name, apt_cmd, timeout=120,
                            )
                            setup_log_parts.append(
                                f"[extra-apt] {apt_cmd}\n"
                                f"rc={dep_proc.returncode}\n"
                                f"stdout: {dep_proc.stdout}\n"
                                f"stderr: {dep_proc.stderr}"
                            )
                            if dep_proc.returncode != 0:
                                print(
                                    f"  Extra apt deps FAILED: "
                                    f"{dep_proc.stderr[:200]}"
                                )
                                setup_ok = False
                        except Exception as e:
                            setup_log_parts.append(
                                f"[extra-apt] EXCEPTION: {e}"
                            )
                            print(f"  Extra apt deps failed: {e}")
                            setup_ok = False

                if setup_ok:
                    extra_pip = task.extra.get("extra_pip_deps", [])
                    if extra_pip:
                        pip_cmd = (
                            "pip install -q "
                            + " ".join(
                                f"'{p}'" for p in extra_pip
                            )
                        )
                        try:
                            dep_proc = docker_exec(
                                container_name, pip_cmd, timeout=120,
                            )
                            setup_log_parts.append(
                                f"[extra-pip] {pip_cmd}\n"
                                f"rc={dep_proc.returncode}\n"
                                f"stdout: {dep_proc.stdout}\n"
                                f"stderr: {dep_proc.stderr}"
                            )
                            if dep_proc.returncode != 0:
                                print(
                                    f"  Extra pip deps FAILED: "
                                    f"{dep_proc.stderr[:200]}"
                                )
                                setup_ok = False
                        except Exception as e:
                            setup_log_parts.append(
                                f"[extra-pip] EXCEPTION: {e}"
                            )
                            print(f"  Extra pip deps failed: {e}")
                            setup_ok = False

                if setup_ok:
                    for cmd in task.setup_commands:
                        print(f"  Setup (docker): {cmd[:80]}...")
                        try:
                            proc = docker_exec(
                                container_name, cmd, timeout=600,
                            )
                            setup_log_parts.append(
                                f"[setup] {cmd[:80]}\n"
                                f"rc={proc.returncode}\n"
                                f"stdout: {proc.stdout}\n"
                                f"stderr: {proc.stderr}"
                            )
                            if proc.returncode != 0:
                                print(
                                    f"  Setup FAILED "
                                    f"(rc={proc.returncode}): "
                                    f"{proc.stderr[:200]}"
                                )
                                setup_ok = False
                                break
                        except Exception as e:
                            setup_log_parts.append(
                                f"[setup] {cmd[:80]}\nEXCEPTION: {e}"
                            )
                            print(f"  Setup failed: {e}")
                            setup_ok = False
                            break
            else:
                # --- Host path: original behavior ---
                for cmd in task.setup_commands:
                    print(f"  Setup: {cmd[:80]}...")
                    try:
                        wrapped_cmd = f"set -o pipefail; {cmd}"
                        proc = subprocess.run(
                            wrapped_cmd, shell=True, cwd=str(sandbox),
                            capture_output=True, text=True, timeout=300,
                            executable="/bin/bash", env=setup_env,
                        )
                        if proc.returncode != 0:
                            print(
                                f"  Setup FAILED "
                                f"(rc={proc.returncode}): "
                                f"{proc.stderr[:200]}"
                            )
                            setup_ok = False
                            break
                    except Exception as e:
                        print(f"  Setup failed: {e}")
                        setup_ok = False

            # Apply test_patch if present (SWE-bench workflow)
            test_patch = task.extra.get("test_patch", "")
            if test_patch and setup_ok:
                repo_name = task.extra.get("repo_name", "")
                patch_dir = sandbox / repo_name if repo_name else sandbox
                if patch_dir.exists():
                    # Write patch file on host (visible in container
                    # via volume mount)
                    patch_file = sandbox / "test_patch.diff"
                    patch_file.write_text(test_patch, encoding="utf-8")

                    if use_docker:
                        # Run git apply inside container — files
                        # are root-owned so host can't overwrite
                        container_patch = (
                            f"/work/{repo_name}"
                            if repo_name else "/work"
                        )
                        try:
                            proc = docker_exec(
                                container_name,
                                "git apply --allow-empty "
                                "--ignore-whitespace "
                                "/work/test_patch.diff",
                                workdir=container_patch,
                                timeout=30,
                            )
                            if proc.returncode == 0:
                                print(
                                    "  Test patch applied "
                                    "successfully (docker)"
                                )
                                test_patch_files = (
                                    _extract_patch_files(test_patch)
                                )
                                if test_patch_files:
                                    task.extra[
                                        "test_patch_files"
                                    ] = test_patch_files
                            else:
                                print(
                                    f"  Test patch FAILED: "
                                    f"{proc.stderr[:200]}"
                                )
                                setup_ok = False
                        except Exception as e:
                            print(f"  Test patch failed: {e}")
                            setup_ok = False
                    else:
                        # Host path — original behavior
                        patch_path_str = str(
                            patch_file,
                        ).replace("\\", "/")
                        try:
                            proc = subprocess.run(
                                f'git apply --allow-empty '
                                f'--ignore-whitespace '
                                f'"{patch_path_str}"',
                                shell=True,
                                cwd=str(patch_dir),
                                capture_output=True,
                                text=True,
                                timeout=30,
                            )
                            if proc.returncode == 0:
                                print(
                                    "  Test patch applied "
                                    "successfully"
                                )
                                test_patch_files = (
                                    _extract_patch_files(test_patch)
                                )
                                if test_patch_files:
                                    task.extra[
                                        "test_patch_files"
                                    ] = test_patch_files
                            else:
                                print(
                                    f"  Test patch FAILED: "
                                    f"{proc.stderr[:200]}"
                                )
                                setup_ok = False
                        except Exception as e:
                            print(f"  Test patch failed: {e}")
                            setup_ok = False

            # Persist full setup log for diagnostics (Finding 3)
            if setup_log_parts:
                setup_log_path = sandbox / "setup_log.txt"
                setup_log_path.write_text(
                    "\n\n".join(setup_log_parts),
                    encoding="utf-8",
                )
                task.extra["_setup_log_path"] = str(setup_log_path)
                print(f"  Setup log: {setup_log_path}")

            # Fix file permissions so host user can run git ops
            if use_docker and container_name and setup_ok:
                fix_permissions(container_name)

            # Inject tool_restriction from lane config into task extra
            tool_restriction = LANE_CONFIGS.get(
                lane, {},
            ).get("tool_restriction")
            if tool_restriction:
                task.extra["tool_restriction"] = tool_restriction

            # Pass container name to adapters for grading
            if use_docker and container_name:
                task.extra["_container_name"] = container_name

            if not setup_ok:
                result = AgentResult(
                    task_id=task.task_id,
                    resolved=False,
                    error="Setup failed",
                    artifacts={
                        "setup_log_path": task.extra.get(
                            "_setup_log_path", "",
                        ),
                    },
                )
            else:
                result = await agent.solve_task(task, sandbox, budget)

        finally:
            # Always clean up Docker container
            if use_docker and container_name:
                stop_and_remove(container_name)

        status = "RESOLVED" if result.resolved else "FAILED"
        if result.error:
            status = f"ERROR: {result.error[:50]}"
            infra_fails += 1

        print(f"  Result: {status} ({result.wall_time_s}s)")

        if result.resolved:
            resolved_count += 1
        total_time += result.wall_time_s

        task_artifacts = dict(result.artifacts or {})
        setup_log = task.extra.get("_setup_log_path", "")
        if setup_log:
            task_artifacts["setup_log_path"] = setup_log

        results.append({
            "task_id": result.task_id,
            "resolved": result.resolved,
            "score": result.score,
            "wall_time_s": result.wall_time_s,
            "tool_calls": result.tool_calls,
            "tokens_in": result.tokens_in,
            "tokens_out": result.tokens_out,
            "error": result.error,
            "artifacts": task_artifacts,
        })

        # Save progress after each task for resumability
        _save_progress(lane, agent.name, results, image_digests)

    # Lane complete — clear progress file
    _clear_progress(lane, agent.name)

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
        "image_digests": image_digests,
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
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from last checkpoint (skip already-completed tasks)",
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

    # Validate lane is executable before spending any compute
    is_executable, not_exec_reason = validate_lane_executable(
        lane, lane_cfg, meta, tasks,
    )
    if not is_executable:
        print(f"\nNOT_EXECUTABLE: {not_exec_reason}")
        # Write a minimal result artifact
        ts = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        report = {
            "lane": lane,
            "status": "NOT_EXECUTABLE",
            "reason": not_exec_reason,
            "total_tasks": len(tasks),
            "timestamp": ts,
        }
        report_path = RESULTS_DIR / f"{ts}-{lane}-NOT_EXECUTABLE.json"
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(report, indent=2), encoding="utf-8",
        )
        print(f"Artifact: {report_path}")
        return 0

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

        # Validate tool_restriction enforcement capability
        tool_restriction = lane_cfg.get("tool_restriction")
        if tool_restriction and agent_name not in ("autocode",):
            print(
                f"BLOCKED: Agent {agent_name} cannot enforce "
                f"tool_restriction={tool_restriction!r}."
            )
            continue

        run_data = await run_lane(
            adapter, lane, tasks, budget, manifest_path,
            resume=args.resume,
        )

        contract = build_run_contract(
            adapter, lane, manifest_path, budget, command_trace,
            image_digests=run_data.get("image_digests"),
        )
        run_data["contract"] = contract

        save_run_report(run_data, contract)
        reports.append(run_data)

    # Print comparison if multiple agents
    if len(reports) > 1:
        print_comparison_table(reports)

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
