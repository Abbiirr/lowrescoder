#!/usr/bin/env python3
"""Run the AutoCode TUI visual snapshot suite.

Modes (CLI flag):

- ``--update`` — capture each scenario and OVERWRITE the stored reference
  PNG. Use sparingly; every update creates a new frozen baseline that
  subsequent diffs compare against.
- (default) — capture each scenario, render to a candidate PNG under
  ``docs/qa/vhs/candidates/<stamp>/``, and diff against the stored
  reference. Exit code is non-zero if any diff exceeds tolerance.

Outputs an artifact markdown summarizing the run under
``autocode/docs/qa/test-results/<stamp>-vhs-visual-suite.md``.

Usage:

  # initial: capture + store references (no diff)
  python3 autocode/tests/vhs/run_visual_suite.py --update

  # regression: diff candidate against stored references
  python3 autocode/tests/vhs/run_visual_suite.py
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

# Allow direct script execution — add the containing dir to sys.path so
# `capture`, `differ`, etc. import as bare modules.
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from capture import capture_scenario  # noqa: E402
from differ import diff_images  # noqa: E402
from renderer import feed_ansi_to_screen, render_screen_to_png  # noqa: E402
from scenarios import SCENARIOS  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]
AUTOCODE_ROOT = REPO_ROOT / "autocode"
GO_TUI = AUTOCODE_ROOT / "cmd" / "autocode-tui" / "autocode-tui"
MOCK_BACKEND = AUTOCODE_ROOT / "tests" / "pty" / "mock_backend.py"
REFERENCE_DIR = AUTOCODE_ROOT / "tests" / "vhs" / "reference"
CANDIDATE_ROOT = AUTOCODE_ROOT / "docs" / "qa" / "vhs" / "candidates"
ARTIFACT_DIR = AUTOCODE_ROOT / "docs" / "qa" / "test-results"

# Pixel-mismatch tolerance per scenario. Default 1% gives enough jitter
# headroom for font/antialias noise.
DEFAULT_PIXEL_RATIO = 0.01


def _env_for_capture() -> dict[str, str]:
    return {"AUTOCODE_PYTHON_CMD": str(MOCK_BACKEND)}


def _capture_one(scenario, stamp: str, *, is_update: bool) -> tuple[Path, dict]:
    ansi = capture_scenario(
        GO_TUI, scenario, env_extra=_env_for_capture(),
    )
    screen = feed_ansi_to_screen(
        ansi, columns=scenario.columns, lines=scenario.lines,
    )
    if is_update:
        out_path = REFERENCE_DIR / f"{scenario.name}.png"
    else:
        run_dir = CANDIDATE_ROOT / stamp
        out_path = run_dir / f"{scenario.name}.png"
    render_screen_to_png(screen, out_path)
    info = {"bytes_captured": len(ansi), "png": str(out_path)}
    return out_path, info


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AutoCode TUI visual suite")
    parser.add_argument(
        "--update",
        action="store_true",
        help="Capture and overwrite the stored reference PNGs (no diff).",
    )
    parser.add_argument(
        "--pixel-ratio",
        type=float,
        default=DEFAULT_PIXEL_RATIO,
        help="Max mismatch ratio per scenario before failure (default 0.01).",
    )
    args = parser.parse_args(argv)

    if not GO_TUI.is_file():
        print(f"ERROR: Go TUI binary not found at {GO_TUI}")
        return 2
    if not MOCK_BACKEND.is_file():
        print(f"ERROR: mock backend not found at {MOCK_BACKEND}")
        return 2

    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    is_update = bool(args.update)
    mode_label = "UPDATE (overwriting references)" if is_update else "DIFF"

    print(f"AutoCode TUI visual suite — {mode_label}")
    print(f"Binary: {GO_TUI}")
    print(f"Reference dir: {REFERENCE_DIR}")

    scenario_results: list[dict] = []
    any_mismatch = False

    for scenario in SCENARIOS:
        print(f"\n[{scenario.name}] capturing …")
        try:
            out_path, meta = _capture_one(scenario, stamp, is_update=is_update)
        except Exception as exc:  # noqa: BLE001 — one scenario failing should not halt the suite
            print(f"  ✗ capture failed: {exc}")
            scenario_results.append({
                "name": scenario.name, "status": "capture_error", "detail": str(exc),
            })
            any_mismatch = True
            continue
        print(f"  ✓ captured {meta['bytes_captured']} ANSI bytes → {out_path}")

        if is_update:
            scenario_results.append({
                "name": scenario.name,
                "status": "reference_updated",
                "png": str(out_path),
                "bytes_captured": meta["bytes_captured"],
            })
            continue

        reference = REFERENCE_DIR / f"{scenario.name}.png"
        if not reference.is_file():
            print(f"  ! no reference at {reference}; run with --update first")
            scenario_results.append({
                "name": scenario.name, "status": "no_reference",
                "candidate": str(out_path),
            })
            any_mismatch = True
            continue

        diff_path = CANDIDATE_ROOT / stamp / f"{scenario.name}.diff.png"
        report = diff_images(reference, out_path, diff_out=diff_path)
        within = report.within_tolerance(pixel_ratio=args.pixel_ratio)
        status = "ok" if within else "mismatch"
        if not within:
            any_mismatch = True
        print(
            f"  {'✓' if within else '✗'} {status} — mismatch "
            f"{report.mismatched_pixels}/{report.total_pixels} "
            f"({report.mismatch_ratio:.4%}), max Δ={report.max_channel_delta}",
        )
        scenario_results.append({
            "name": scenario.name,
            "status": status,
            "reference": str(reference),
            "candidate": str(out_path),
            "diff_image": str(diff_path),
            "mismatched_pixels": report.mismatched_pixels,
            "total_pixels": report.total_pixels,
            "mismatch_ratio": round(report.mismatch_ratio, 6),
            "max_channel_delta": report.max_channel_delta,
            "within_tolerance": within,
        })

    # Write a run-summary markdown artifact
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    artifact_path = ARTIFACT_DIR / f"{stamp}-vhs-visual-suite.md"
    lines = [f"# TUI Visual Suite — {stamp}\n"]
    lines.append(f"Mode: {mode_label}\n")
    lines.append(f"Binary: `{GO_TUI}`\n")
    lines.append(f"Scenarios: {len(scenario_results)}\n")
    if not is_update:
        ok_count = sum(
            1 for r in scenario_results if r.get("status") == "ok"
        )
        lines.append(f"OK: {ok_count}/{len(scenario_results)}\n")
    lines.append("\n## Per-scenario results\n")
    for result in scenario_results:
        lines.append(
            f"- **{result['name']}** — status: `{result['status']}`",
        )
        for key, value in result.items():
            if key in {"name", "status"}:
                continue
            lines.append(f"  - {key}: `{value}`")
    artifact_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nArtifact: {artifact_path}")

    return 1 if any_mismatch and not is_update else 0


if __name__ == "__main__":
    sys.exit(main())
