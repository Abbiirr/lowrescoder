#!/usr/bin/env python3
"""Capture the current AutoCode analog for all 14 reference scenes.

This is intentionally not the same as Track 4 scene promotion. The goal here
is to store a truthful snapshot of what the current product can show for each
reference scene:

- direct matchable surfaces
- approximate current analogs
- partial or negative evidence where the surface does not exist yet
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


_HERE = Path(__file__).resolve().parent
_AUTOCODE_ROOT = _HERE.parents[1]
_REPO_ROOT = _AUTOCODE_ROOT.parent
_FRAME_ROOT = _AUTOCODE_ROOT / "docs" / "qa" / "tui-frame-sequences"
_RESULTS_ROOT = _AUTOCODE_ROOT / "docs" / "qa" / "test-results"
_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"


@dataclass(frozen=True)
class SceneAttempt:
    scene_id: str
    label: str
    result_kind: str
    trigger: str
    note: str
    preset: str | None = None
    steps_literal: str | None = None
    preferred_frames: tuple[str, ...] = (
        "05-final",
        "04-final",
        "03-final",
        "04-sleep",
        "03-sleep",
        "02-final",
        "02-sleep",
        "04-input",
        "03-input",
        "02-input",
        "01-input",
        "01-sleep",
        "00-boot",
    )


def scene_attempts() -> list[SceneAttempt]:
    return [
        SceneAttempt("ready", "01 Ready", "direct", "preset:ready", "Direct idle startup surface.", preset="ready"),
        SceneAttempt("active", "02 Active", "direct", "preset:active", "Direct mid-run working state.", preset="active", preferred_frames=("02-sleep", "03-final", "01-input")),
        SceneAttempt("multi", "03 Multitasking", "direct", "preset:multi", "Dedicated multitasking / queue-pressure surface.", preset="multi"),
        SceneAttempt("plan", "04 Plan", "direct", "preset:plan", "Dedicated plan surface with queued and active steps.", preset="plan"),
        SceneAttempt("review", "05 Review", "direct", "preset:review", "Dedicated review surface with first-class approval actions.", preset="review"),
        SceneAttempt("cc", "06 Command center", "direct", "preset:cc", "Dedicated command-center surface with subagent and risk sections.", preset="cc"),
        SceneAttempt("recovery", "07 Recovery", "direct", "preset:recovery", "Direct halted recovery surface.", preset="recovery"),
        SceneAttempt("restore", "08 Restore", "direct", "preset:restore", "Dedicated restore browser with checkpoint inventory.", preset="restore"),
        SceneAttempt("sessions", "09 Sessions", "direct", "preset:sessions", "Direct session-picker overlay.", preset="sessions"),
        SceneAttempt("palette", "10 Palette", "direct", "preset:palette", "Direct command-palette overlay.", preset="palette"),
        SceneAttempt("diff", "11 Diff focus", "direct", "preset:diff", "Dedicated diff-focus surface with file/hunk review controls.", preset="diff"),
        SceneAttempt("grep", "12 Search", "direct", "preset:grep", "Dedicated search / grep investigation surface.", preset="grep"),
        SceneAttempt("escalation", "13 Escalation", "direct", "preset:escalation", "Dedicated protected-path escalation surface.", preset="escalation"),
        SceneAttempt("narrow", "14 Narrow", "direct", "preset:narrow", "Direct narrow-width idle surface.", preset="narrow"),
    ]


def _run_capture(item: SceneAttempt, stamp: str) -> Path:
    cmd = [sys.executable, "tests/tui-references/capture_frame_sequence.py", "--stamp", stamp]
    if item.preset is not None:
        cmd.extend(["--preset", item.preset])
    else:
        cmd.extend(["--name", item.scene_id, "--steps", item.steps_literal or "[]"])
    subprocess.run(cmd, cwd=_AUTOCODE_ROOT, check=True)
    return _FRAME_ROOT / stamp / item.scene_id


def _pick_primary(scene_dir: Path, preferred_frames: tuple[str, ...]) -> tuple[Path, Path]:
    for prefix in preferred_frames:
        png = scene_dir / f"{prefix}.png"
        txt = scene_dir / f"{prefix}.txt"
        if png.exists() and txt.exists():
            return png, txt
    pngs = sorted(scene_dir.glob("*.png"))
    txts = sorted(scene_dir.glob("*.txt"))
    if not pngs or not txts:
        raise FileNotFoundError(f"no frame outputs found in {scene_dir}")
    return pngs[-1], txts[-1]


def _make_grid(items: list[tuple[str, Image.Image]], output: Path) -> None:
    if not items:
        return
    font = ImageFont.truetype(_FONT, 14)
    framed: list[Image.Image] = []
    for label, image in items:
        thumb = image.resize((max(1, int(image.width * (220 / image.height))), 220), Image.LANCZOS)
        canvas = Image.new("RGB", (thumb.width, thumb.height + 36), (18, 18, 18))
        canvas.paste(thumb, (0, 36))
        draw = ImageDraw.Draw(canvas)
        draw.text((8, 8), label, font=font, fill=(240, 240, 240))
        framed.append(canvas)
    cols = 2
    rows = (len(framed) + cols - 1) // cols
    cell_w = max(img.width for img in framed)
    cell_h = max(img.height for img in framed)
    grid = Image.new("RGB", (cols * cell_w + (cols + 1) * 16, rows * cell_h + (rows + 1) * 16), (10, 10, 10))
    for idx, img in enumerate(framed):
        x = 16 + (idx % cols) * (cell_w + 16)
        y = 16 + (idx // cols) * (cell_h + 16)
        grid.paste(img, (x, y))
    output.parent.mkdir(parents=True, exist_ok=True)
    grid.save(output)


def render_report(stamp: str, rows: list[dict[str, str]], grid_path: Path) -> str:
    lines = [
        f"# AutoCode 14-Scene Current-State Capture Matrix — {stamp}",
        "",
        "This artifact stores the current AutoCode analog for all 14 reference scenes.",
        "It is intentionally honest about three cases:",
        "",
        "- direct current surfaces",
        "- approximate current analogs",
        "- partial or negative evidence where the reference surface does not exist yet",
        "",
        "## Outputs",
        "",
        f"- Frame root: `{_FRAME_ROOT / stamp}`",
        f"- Overview grid: `{grid_path}`",
        "",
        "## Scene Table",
        "",
        "| Scene | Result kind | Trigger used | Primary PNG | Primary TXT | Note |",
        "|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| `{row['scene_id']}` | `{row['result_kind']}` | `{row['trigger']}` | "
            f"`{row['primary_png']}` | `{row['primary_txt']}` | {row['note']} |"
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Capture all 14 current AutoCode scene analogs")
    parser.add_argument("--stamp", default="", help="Optional timestamp override")
    args = parser.parse_args(argv)

    stamp = args.stamp or datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    attempts = scene_attempts()
    rows: list[dict[str, str]] = []
    grid_items: list[tuple[str, Image.Image]] = []

    for item in attempts:
        scene_dir = _run_capture(item, stamp)
        primary_png, primary_txt = _pick_primary(scene_dir, item.preferred_frames)
        grid_items.append((f"{item.scene_id} [{item.result_kind}]", Image.open(primary_png).convert("RGB")))
        rows.append(
            {
                "scene_id": item.scene_id,
                "result_kind": item.result_kind,
                "trigger": item.trigger,
                "primary_png": str(primary_png),
                "primary_txt": str(primary_txt),
                "note": item.note,
            }
        )

    grid_path = _FRAME_ROOT / stamp / "scene-matrix-grid.png"
    _make_grid(grid_items, grid_path)

    report = render_report(stamp, rows, grid_path)
    report_path = _RESULTS_ROOT / f"{stamp}-tui-14-scene-capture-matrix.md"
    report_path.write_text(report, encoding="utf-8")
    print(report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
