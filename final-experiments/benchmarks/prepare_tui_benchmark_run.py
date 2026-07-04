#!/usr/bin/env python3
"""Prepare a human-operated benchmark run through the Rust TUI.

This script does not execute the benchmark tasks. It performs preflight
checks, prints the canonical commands for the chosen sweep, and emits an
operator pack with per-lane / per-task notes so a human can prepare the suite
honestly before running it through the TUI.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

REPO_ROOT = Path(__file__).resolve().parent.parent
AUTOCODE_ROOT = REPO_ROOT / "autocode"
RESULTS_DIR = REPO_ROOT / "docs" / "qa" / "test-results"
TUI_BIN = AUTOCODE_ROOT / "rtui" / "target" / "release" / "autocode-tui"
RUNNER = REPO_ROOT / "benchmarks" / "benchmark_runner.py"
CORE_SWEEP = REPO_ROOT / "benchmarks" / "run_all_benchmarks.sh"
FULL_SWEEP = REPO_ROOT / "benchmarks" / "run_b7_b30_sweep.sh"
REAL_GATEWAY_SMOKE = AUTOCODE_ROOT / "tests" / "pty" / "pty_e2e_real_gateway.py"
AUTH_KEYS = ("LITELLM_API_KEY", "LITELLM_MASTER_KEY", "OPENROUTER_API_KEY")

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from benchmarks.adapters.base import BenchmarkTask, load_manifest  # noqa: E402
from benchmarks.benchmark_runner import LANE_CONFIGS, MANIFEST_DIR  # noqa: E402


@dataclass(frozen=True)
class ScopeConfig:
    name: str
    label: str
    lanes: tuple[str, ...]
    sweep_script: Path


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str


CORE_SCOPE = ScopeConfig(
    name="core",
    label="B7-B14 core sweep",
    lanes=(
        "B7",
        "B8",
        "B9-PROXY",
        "B10-PROXY",
        "B11",
        "B12-PROXY",
        "B13-PROXY",
        "B14-PROXY",
    ),
    sweep_script=CORE_SWEEP,
)

FULL_SCOPE = ScopeConfig(
    name="full",
    label="B7-B30 full sweep",
    lanes=(
        "B7",
        "B8",
        "B9-PROXY",
        "B10-PROXY",
        "B11",
        "B12-PROXY",
        "B13-PROXY",
        "B14-PROXY",
        "B15",
        "B16",
        "B17",
        "B18",
        "B19",
        "B20",
        "B21",
        "B22",
        "B23",
        "B24",
        "B25",
        "B26",
        "B27",
        "B28",
        "B29",
        "B30-TBENCH",
    ),
    sweep_script=FULL_SWEEP,
)

SCOPES = {
    "core": CORE_SCOPE,
    "full": FULL_SCOPE,
}


def get_scope(scope_name: str) -> ScopeConfig:
    try:
        return SCOPES[scope_name]
    except KeyError as exc:
        raise ValueError(f"unknown scope: {scope_name}") from exc


def generate_run_id() -> str:
    return f"{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}-{os.getpid()}"


def select_auth_source(env: dict[str, str]) -> str | None:
    for key in AUTH_KEYS:
        if env.get(key):
            return key
    return None


def load_benchmark_env() -> dict[str, str]:
    env = os.environ.copy()
    env_file = REPO_ROOT / ".env"
    if not env_file.exists():
        return env

    proc = subprocess.run(
        [
            "bash",
            "-lc",
            f"set -a && source {shlex.quote(str(env_file))} && env",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    if proc.returncode != 0:
        return env

    merged = env.copy()
    for line in proc.stdout.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        merged[key] = value
    return merged


def benchmark_host(env: dict[str, str]) -> str:
    return env.get("AUTOCODE_LLM_API_BASE") or env.get(
        "OLLAMA_HOST",
        "http://localhost:4000/v1",
    )


def gateway_health_url(env: dict[str, str]) -> str:
    host = benchmark_host(env)
    return f"{host.removesuffix('/v1')}/health/readiness"


def lane_model(lane: str) -> str:
    return "terminal_bench" if lane == "B30-TBENCH" else "swebench"


def tui_launch_command(mode: str) -> str:
    if mode == "altscreen":
        return "uv run autocode chat --rust-altscreen"
    return "uv run autocode chat"


def alternate_tui_command(mode: str) -> str:
    if mode == "altscreen":
        return "uv run autocode chat"
    return "uv run autocode chat --rust-altscreen"


def build_operator_commands(
    *,
    scope: ScopeConfig,
    mode: str,
    run_id: str,
    canary_tasks: int,
) -> dict[str, str]:
    first_lane = scope.lanes[0]
    first_model = lane_model(first_lane)
    sweep_cmd = f"BENCHMARK_RUN_ID={run_id} bash {scope.sweep_script.relative_to(REPO_ROOT)}"
    lane_case = " ".join(scope.lanes)
    tui_sweep_cmd = (
        f"BENCHMARK_RUN_ID={run_id} bash -lc '"
        f"for lane in {lane_case}; do "
        "if [ \"$lane\" = \"B30-TBENCH\" ]; then model=terminal_bench; else model=swebench; fi; "
        "uv run python benchmarks/benchmark_runner.py "
        "--agent autocode --autocode-runner tui "
        "--lane \"$lane\" --model \"$model\" "
        f"--run-id {run_id} --resume || exit $?; "
        "done'"
    )
    return {
        "tui_warmup": tui_launch_command(mode),
        "tui_alternate_mode": alternate_tui_command(mode),
        "list_lanes": "uv run python benchmarks/benchmark_runner.py --list-lanes",
        "real_gateway_smoke": (
            "cd autocode && uv run python tests/pty/pty_e2e_real_gateway.py"
        ),
        "canary_lane": (
            f"BENCHMARK_RUN_ID={run_id} "
            "uv run python benchmarks/benchmark_runner.py "
            f"--agent autocode --lane {first_lane} "
            f"--max-tasks {canary_tasks} --model {first_model} "
            f"--run-id {run_id} --resume"
        ),
        "tui_canary_lane": (
            f"BENCHMARK_RUN_ID={run_id} "
            "uv run python benchmarks/benchmark_runner.py "
            f"--agent autocode --autocode-runner tui --lane {first_lane} "
            f"--max-tasks {canary_tasks} --model {first_model} "
            f"--run-id {run_id} --resume"
        ),
        "sweep": sweep_cmd,
        "tui_sweep": tui_sweep_cmd,
        "resume": sweep_cmd,
    }


def check_path_exists(name: str, path: Path) -> CheckResult:
    return CheckResult(name=name, ok=path.exists(), detail=str(path))


def check_gateway(env: dict[str, str]) -> CheckResult:
    url = gateway_health_url(env)
    try:
        with urlopen(url, timeout=5) as response:  # noqa: S310
            body = response.read().decode("utf-8", errors="replace")
    except URLError as exc:
        return CheckResult("gateway_health", False, f"{url} ({exc})")

    healthy = "healthy" in body.lower()
    return CheckResult("gateway_health", healthy, f"{url} -> {body.strip()[:120]}")


def check_runner_list_lanes() -> CheckResult:
    proc = subprocess.run(
        ["uv", "run", "python", "benchmarks/benchmark_runner.py", "--list-lanes"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    detail = (proc.stdout or proc.stderr).strip().splitlines()
    tail = detail[0] if detail else f"rc={proc.returncode}"
    return CheckResult("benchmark_runner_list_lanes", proc.returncode == 0, tail)


def run_real_gateway_smoke() -> CheckResult:
    proc = subprocess.run(
        ["uv", "run", "python", "tests/pty/pty_e2e_real_gateway.py"],
        cwd=AUTOCODE_ROOT,
        capture_output=True,
        text=True,
        timeout=240,
        check=False,
    )
    combined = "\n".join(
        part.strip()
        for part in (proc.stdout, proc.stderr)
        if part and part.strip()
    )
    detail = combined.splitlines()[-1] if combined else f"rc={proc.returncode}"
    return CheckResult("real_gateway_smoke", proc.returncode == 0, detail)


def manifest_prompt_hint(task: BenchmarkTask, manifest_path: Path) -> str | None:
    fixture_dir = task.extra.get("fixture_dir")
    if fixture_dir:
        candidate = (manifest_path.parent / fixture_dir / "prompt.md").resolve()
        if candidate.exists():
            return display_path(candidate)
    return None


def safe_task_filename(lane: str, task_id: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in "-._" else "_" for ch in task_id)
    return f"{lane}--{cleaned}.md"


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def task_markdown(
    *,
    lane: str,
    task: BenchmarkTask,
    manifest_path: Path,
    mode: str,
) -> str:
    setup = task.setup_commands or []
    prompt_hint = manifest_prompt_hint(task, manifest_path)
    lines = [
        f"# {lane} · {task.task_id}",
        "",
        f"- Description: {task.description}",
        f"- Model alias: `{lane_model(lane)}`",
        f"- Mode for primary TUI launch: `{mode}`",
        f"- Canonical TUI launch: `{tui_launch_command(mode)}`",
        f"- Alternate TUI launch: `{alternate_tui_command(mode)}`",
        f"- Manifest: `{display_path(manifest_path)}`",
    ]
    if task.repo:
        lines.append(f"- Repo: `{task.repo}`")
    if task.difficulty:
        lines.append(f"- Difficulty: `{task.difficulty}`")
    if task.language:
        lines.append(f"- Language: `{task.language}`")
    if task.category:
        lines.append(f"- Category: `{task.category}`")
    if prompt_hint:
        lines.append(f"- Prompt hint: `{prompt_hint}`")
    for key in ("repo_name", "python_version", "docker_image", "fixture_dir", "base_commit"):
        value = task.extra.get(key)
        if value:
            lines.append(f"- {key}: `{value}`")

    lines.extend(["", "## Setup Commands", ""])
    if setup:
        lines.append("```bash")
        lines.extend(setup)
        lines.append("```")
    else:
        lines.append("_No extra setup commands recorded in the manifest._")

    lines.extend(["", "## Grading Command", "", "```bash"])
    lines.append(task.grading_command or "# No grading command recorded")
    lines.append("```")

    lines.extend([
        "",
        "## Operator Notes",
        "",
        "- This pack prepares the suite honestly, but it does not clone repos, build Docker sandboxes, or apply `test_patch` automatically.",
        "- For canonical setup and grading, keep using the benchmark harness commands from the pack index.",
        "- Use this task file as the prompt / grading reference when you drive the task manually through the TUI.",
    ])
    return "\n".join(lines) + "\n"


def emit_operator_pack(
    *,
    pack_dir: Path,
    scope: ScopeConfig,
    mode: str,
    run_id: str,
    commands: dict[str, str],
    manifests: dict[str, tuple[Path, dict[str, Any], list[BenchmarkTask]]],
    checks: list[CheckResult],
) -> None:
    pack_dir.mkdir(parents=True, exist_ok=True)
    tasks_dir = pack_dir / "tasks"
    tasks_dir.mkdir(exist_ok=True)

    total_tasks = 0
    lane_summaries: list[str] = []
    for lane in scope.lanes:
        manifest_path, meta, tasks = manifests[lane]
        total_tasks += len(tasks)
        task_paths: list[str] = []
        for task in tasks:
            filename = safe_task_filename(lane, task.task_id)
            task_path = tasks_dir / filename
            task_path.write_text(
                task_markdown(
                    lane=lane,
                    task=task,
                    manifest_path=manifest_path,
                    mode=mode,
                ),
                encoding="utf-8",
            )
            task_paths.append(f"`tasks/{filename}`")

        lane_summaries.append(
            "\n".join([
                f"### {lane}",
                f"- Manifest: `{display_path(manifest_path)}`",
                f"- Tasks: `{len(tasks)}`",
                f"- Runner: `{LANE_CONFIGS[lane].get('runner', 'unspecified')}`",
                f"- Model alias: `{lane_model(lane)}`",
                f"- Meta keys: `{', '.join(sorted(meta.keys())) or 'none'}`",
                f"- Task notes: {', '.join(task_paths[:5])}"
                + (" ..." if len(task_paths) > 5 else ""),
            ])
        )

    lines = [
        f"# TUI Benchmark Operator Pack · {scope.label}",
        "",
        f"- Run ID: `{run_id}`",
        f"- Primary TUI mode: `{mode}`",
        f"- Lane count: `{len(scope.lanes)}`",
        f"- Task count: `{total_tasks}`",
        "",
        "## Preflight",
        "",
    ]
    for check in checks:
        status = "OK" if check.ok else "FAIL"
        lines.append(f"- `{status}` {check.name}: {check.detail}")

    lines.extend(["", "## Canonical Commands", ""])
    for key, value in commands.items():
        lines.append(f"- `{key}`: `{value}`")

    lines.extend([
        "",
        "## Scope Notes",
        "",
        "- The generated task notes are for human prep and prompt fidelity.",
        "- Canonical setup, sandbox creation, resume behavior, and JSON result artifacts still belong to the benchmark harness.",
        "- Inline mode preserves native scrollback. Alt-screen mode is available when you want a dedicated fullscreen session.",
        "- `tui_canary_lane` is the benchmark-owned PTY automation path that launches `autocode chat --rust-altscreen` from the harness.",
        "",
        "## Lanes",
        "",
        *lane_summaries,
        "",
    ])
    (pack_dir / "index.md").write_text("\n".join(lines), encoding="utf-8")


def load_scope_manifests(
    scope: ScopeConfig,
) -> dict[str, tuple[Path, dict[str, Any], list[BenchmarkTask]]]:
    manifests: dict[str, tuple[Path, dict[str, Any], list[BenchmarkTask]]] = {}
    for lane in scope.lanes:
        manifest_path = (MANIFEST_DIR / LANE_CONFIGS[lane]["manifest"]).resolve()
        meta, tasks = load_manifest(manifest_path)
        manifests[lane] = (manifest_path, meta, tasks)
    return manifests


def render_human_summary(
    *,
    scope: ScopeConfig,
    mode: str,
    run_id: str,
    pack_dir: Path,
    commands: dict[str, str],
    checks: list[CheckResult],
) -> str:
    lines = [
        "TUI benchmark prep",
        f"- scope: {scope.label}",
        f"- mode: {mode}",
        f"- run_id: {run_id}",
        f"- operator_pack: {pack_dir.relative_to(REPO_ROOT)}",
        "Checks:",
    ]
    for check in checks:
        prefix = "OK" if check.ok else "FAIL"
        lines.append(f"  - [{prefix}] {check.name}: {check.detail}")
    lines.append("Commands:")
    for key, value in commands.items():
        lines.append(f"  - {key}: {value}")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare a human-operated benchmark run through the Rust TUI.",
    )
    parser.add_argument(
        "--scope",
        choices=sorted(SCOPES),
        default="full",
        help="Benchmark scope to prepare.",
    )
    parser.add_argument(
        "--mode",
        choices=("inline", "altscreen"),
        default="inline",
        help="Preferred TUI mode for operator launches.",
    )
    parser.add_argument(
        "--run-id",
        default="",
        help="Explicit run id to embed in commands and the operator pack.",
    )
    parser.add_argument(
        "--canary-tasks",
        type=int,
        default=1,
        help="Task count for the suggested canary lane command.",
    )
    parser.add_argument(
        "--skip-smoke",
        action="store_true",
        help="Skip the real-gateway PTY smoke probe.",
    )
    parser.add_argument(
        "--skip-gateway",
        action="store_true",
        help="Skip the gateway readiness check.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON instead of human-readable text.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero if any required preflight check fails.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    scope = get_scope(args.scope)
    benchmark_env = load_benchmark_env()
    run_id = args.run_id or generate_run_id()
    commands = build_operator_commands(
        scope=scope,
        mode=args.mode,
        run_id=run_id,
        canary_tasks=args.canary_tasks,
    )

    checks = [
        check_path_exists("benchmark_runner", RUNNER),
        check_path_exists("sweep_script", scope.sweep_script),
        check_path_exists("rust_tui_binary", TUI_BIN),
        check_path_exists("real_gateway_smoke_script", REAL_GATEWAY_SMOKE),
    ]

    auth_key = select_auth_source(benchmark_env)
    checks.append(
        CheckResult(
            "gateway_auth_env",
            auth_key is not None,
            auth_key or "missing LITELLM_API_KEY / LITELLM_MASTER_KEY / OPENROUTER_API_KEY",
        )
    )

    if args.skip_gateway:
        checks.append(CheckResult("gateway_health", True, "skipped by flag"))
    else:
        checks.append(check_gateway(benchmark_env))

    checks.append(check_runner_list_lanes())

    if args.skip_smoke:
        checks.append(CheckResult("real_gateway_smoke", True, "skipped by flag"))
    else:
        checks.append(run_real_gateway_smoke())

    manifests = load_scope_manifests(scope)
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    pack_dir = RESULTS_DIR / f"{timestamp}-tui-benchmark-pack-{scope.name}-{args.mode}"
    emit_operator_pack(
        pack_dir=pack_dir,
        scope=scope,
        mode=args.mode,
        run_id=run_id,
        commands=commands,
        manifests=manifests,
        checks=checks,
    )

    payload = {
        "scope": {
            "name": scope.name,
            "label": scope.label,
            "lanes": list(scope.lanes),
            "sweep_script": str(scope.sweep_script),
        },
        "mode": args.mode,
        "run_id": run_id,
        "pack_dir": str(pack_dir),
        "checks": [asdict(check) for check in checks],
        "commands": commands,
    }

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(
            render_human_summary(
                scope=scope,
                mode=args.mode,
                run_id=run_id,
                pack_dir=pack_dir,
                commands=commands,
                checks=checks,
            )
        )

    if args.strict and not all(check.ok for check in checks):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
