"""CLI runner for tui-comparison Track 1.

Usage:

    python -m autocode.tests.tui_comparison.run <scenario> [--out <dir>]

Spawns autocode TUI via the launcher, captures a scenario, and writes
the 5 artifacts to
``autocode/docs/qa/tui-comparison/regression/<run-id>/<scenario>/``:

    autocode.raw             # raw ANSI bytes
    autocode.txt             # stripped text (pyte Screen.display)
    autocode.png             # rendered PNG (optional — skip if Pillow absent)
    autocode.profile.yaml    # TermProfile
    predicates.json          # hard + soft classified verdicts
"""
from __future__ import annotations

import argparse
import datetime
import importlib
import os
import re
import sys
from pathlib import Path

# Make this module importable as either `autocode.tests.tui_comparison.run`
# or via `python run.py` with sys.path hacking.
_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

from capture import CaptureOptions, capture  # noqa: E402
from launchers import autocode as autocode_launcher  # noqa: E402
from predicates import render_screen, run_predicates  # noqa: E402
from profile import TermProfile  # noqa: E402  # noqa: F401 — alias resolved below

# `profile` above collides with the stdlib `profile` module. Resolve
# explicitly through the local path.


SCENARIO_MODULES = {
    "startup": "scenarios.startup",
    "first-prompt-text": "scenarios.first_prompt_text",
    "model-picker": "scenarios.model_picker",
    "ask-user-prompt": "scenarios.ask_user_prompt",
    "error-state": "scenarios.error_state",
    "orphaned-startup": "scenarios.orphaned_startup",
    "spinner-cadence": "scenarios.spinner_cadence",
}


def strip_ansi(data: bytes, *, rows: int = 50, cols: int = 160) -> str:
    """Pyte-rendered plain text — authoritative clean view of the capture.

    Delegates to the same pyte pipeline the predicates use so the ``.txt``
    artifact matches what the hard/soft checks see. Codex Entry 1147
    Concern #3 required this fix: the old regex-only strip left
    ``\\x1b[?2026$p`` and ``\\x1b[>4;2m`` sequences in the output.
    """
    _, text = render_screen(data, rows, cols)
    # pyte emits fixed-width lines; strip trailing whitespace per line for
    # diff-friendliness.
    return "\n".join(line.rstrip() for line in text.split("\n")).rstrip() + "\n"


def run_scenario(
    scenario_name: str,
    *,
    out_root: Path,
    rows: int = 50,
    cols: int = 160,
) -> dict:
    """Run one scenario end-to-end; return dict summary for stdout."""
    if scenario_name not in SCENARIO_MODULES:
        raise SystemExit(
            f"unknown scenario {scenario_name!r}; known: {list(SCENARIO_MODULES)}"
        )

    scenario_module = importlib.import_module(SCENARIO_MODULES[scenario_name])
    scen = scenario_module.spec()
    # Scenarios may optionally override the launcher spec (e.g., to use a
    # silent backend or a larger boot_budget_s). Default is the standard
    # mock-backed launcher.
    launcher_kwargs = getattr(scenario_module, "LAUNCHER_KWARGS", {})
    launch = autocode_launcher.spec(**launcher_kwargs)

    opts = CaptureOptions(
        argv=launch.argv,
        cols=cols,
        rows=rows,
        boot_budget_s=launch.boot_budget_s,
        drain_quiet_s=scen.drain_quiet_s,
        drain_maxwait_s=scen.drain_maxwait_s,
        env_extra=launch.env_extra,
        steps=list(scen.steps),
    )

    # Run capture
    result = capture(opts)

    # Build terminal profile
    profile = TermProfile.from_env(
        rows=rows,
        cols=cols,
        boot_budget_s=launch.boot_budget_s,
        tool=launch.tool,
        tool_version=launch.tool_version,
        scenario=scen.name,
    )
    profile.update_dsr(result.dsr_shim_version, result.dsr_responses_served)

    # Artifact directory
    run_id = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    scen_dir = out_root / f"regression/{run_id}/{scen.name}"
    scen_dir.mkdir(parents=True, exist_ok=True)

    # 1. raw ANSI bytes
    (scen_dir / f"{launch.tool}.raw").write_bytes(result.raw)

    # 2. stripped text (via pyte — matches what predicates see)
    text = strip_ansi(result.raw, rows=rows, cols=cols)
    (scen_dir / f"{launch.tool}.txt").write_text(text)

    # 3. profile YAML
    profile.write(scen_dir / f"{launch.tool}.profile.yaml")

    # 4. predicates.json — pass scenario so turn-scoped predicates N/A correctly
    report = run_predicates(result.raw, scenario=scen.name, rows=rows, cols=cols)
    report.write(scen_dir / "predicates.json")

    # 5. PNG (optional — only if Pillow + the existing renderer are importable)
    png_path: Path | None = None
    try:
        _render_png(result.raw, rows, cols, scen_dir / f"{launch.tool}.png")
        png_path = scen_dir / f"{launch.tool}.png"
    except Exception as e:
        # Non-fatal — raw + txt are the primary artifacts
        (scen_dir / f"{launch.tool}.png.skipped").write_text(f"PNG render skipped: {e}\n")

    return {
        "run_id": run_id,
        "scenario": scen.name,
        "tool": launch.tool,
        "raw_bytes": len(result.raw),
        "text_chars": len(text),
        "dsr_served": result.dsr_responses_served,
        "exit_code": result.exit_code,
        "wall_seconds": round(result.wall_seconds, 2),
        "hard_passed": report.all_hard_passed,
        "hard_summary": f"{sum(1 for r in report.hard if r.passed)}/{len(report.hard)}",
        "soft_summary": f"{sum(1 for r in report.soft if r.passed)}/{len(report.soft)}",
        "artifacts_dir": str(scen_dir),
        "png_written": bool(png_path),
    }


def _render_png(raw: bytes, rows: int, cols: int, out_path: Path) -> None:
    """Render captured ANSI to PNG via pyte + Pillow (reuses tests/vhs/renderer)."""
    # Import from the sibling vhs package
    vhs_dir = _THIS_DIR.parent / "vhs"
    if str(vhs_dir) not in sys.path:
        sys.path.insert(0, str(vhs_dir))
    from renderer import render_screen_to_png  # type: ignore[import-not-found]

    screen, _ = render_screen(raw, rows, cols)
    render_screen_to_png(screen, out_path)


def main() -> int:
    parser = argparse.ArgumentParser(description="tui-comparison Track 1 runner")
    parser.add_argument("scenario", choices=list(SCENARIO_MODULES))
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "docs" / "qa" / "tui-comparison",
        help="Artifact output root (default: autocode/docs/qa/tui-comparison)",
    )
    parser.add_argument("--rows", type=int, default=50)
    parser.add_argument("--cols", type=int, default=160)
    args = parser.parse_args()

    summary = run_scenario(
        args.scenario,
        out_root=args.out,
        rows=args.rows,
        cols=args.cols,
    )
    print(f"[tui-comparison] {summary['tool']} · {summary['scenario']}")
    print(f"  wall       : {summary['wall_seconds']}s")
    print(f"  raw bytes  : {summary['raw_bytes']}")
    print(f"  text chars : {summary['text_chars']}")
    print(f"  dsr served : {summary['dsr_served'] or '(none)'}")
    print(f"  hard       : {summary['hard_summary']} passed")
    print(f"  soft       : {summary['soft_summary']} passed (failures = Track 3 gap items)")
    print(f"  artifacts  : {summary['artifacts_dir']}")
    return 0 if summary["hard_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
