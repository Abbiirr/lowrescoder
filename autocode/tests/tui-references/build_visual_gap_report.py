#!/usr/bin/env python3
"""Build a screenshot-first TUI vs reference comparison bundle.

This is a manual, evidence-generation helper for frequent visual reviews.
It is not a regression gate by itself. Instead it packages:

1. deterministic live TUI captures (PNG + text),
2. side-by-side sheets pairing reference JPG exports with live captures,
3. a markdown artifact under ``autocode/docs/qa/test-results/``.

The generated artifact is intended to answer:
"What does the current Rust TUI actually look like against the
`tui-references` mockup pages, scene by scene?"
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

_HERE = Path(__file__).resolve().parent
_AUTOCODE_ROOT = _HERE.parents[1]
_REPO_ROOT = _AUTOCODE_ROOT.parent
_VHS_DIR = _AUTOCODE_ROOT / "tests" / "vhs"
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
if str(_VHS_DIR) not in sys.path:
    sys.path.insert(0, str(_VHS_DIR))

from capture import Scenario, capture_scenario  # type: ignore  # noqa: E402
from renderer import feed_ansi_to_screen, render_screen_to_png  # type: ignore  # noqa: E402
from scene_presets import get_scene_preset  # type: ignore  # noqa: E402


DEFAULT_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
REFERENCE_DIR = _REPO_ROOT / "tui-references"
RESULTS_DIR = _AUTOCODE_ROOT / "docs" / "qa" / "test-results"
ASSET_ROOT = _AUTOCODE_ROOT / "docs" / "qa" / "tui-reference-comparison"


@dataclass(frozen=True)
class LiveCaptureSpec:
    key: str
    scenario: Scenario
    note: str = ""


@dataclass(frozen=True)
class SceneCompareSpec:
    scene_id: str
    label: str
    reference_page: str
    live_key: str | None
    capture_mode: str
    note: str


@dataclass(frozen=True)
class SceneArtifact:
    spec: SceneCompareSpec
    reference_path: Path
    live_path: Path | None
    compare_path: Path


def resolve_tui_binary() -> Path:
    override = os.environ.get("AUTOCODE_TUI_BIN", "").strip()
    if override:
        return Path(override)
    return _AUTOCODE_ROOT / "rtui" / "target" / "release" / "autocode-tui"


def supplementary_live_keys() -> list[str]:
    return [
        "ready",
        "active",
        "multi",
        "plan",
        "review",
        "cc",
        "restore",
        "diff",
        "grep",
        "escalation",
        "narrow",
        "recovery",
        "sessions",
        "palette",
        "model_picker_open",
        "model_picker_filtered",
        "provider_picker_open",
        "ask_user",
        "warning",
    ]


def _scenario_from_preset(name: str) -> Scenario:
    preset = get_scene_preset(name)
    return Scenario(
        name=preset.scene_id,
        steps=list(preset.steps),
        drain_quiet_s=preset.drain_quiet,
        drain_maxwait_s=preset.drain_maxwait,
        columns=preset.cols,
        lines=preset.rows,
        graceful_exit=False,
    )


def build_live_capture_specs() -> dict[str, LiveCaptureSpec]:
    return {
        "ready": LiveCaptureSpec(
            key="ready",
            scenario=_scenario_from_preset("ready"),
            note="Startup / idle continuity.",
        ),
        "active": LiveCaptureSpec(
            key="active",
            scenario=_scenario_from_preset("active"),
            note="Mid-run working state held open by the slow fixture.",
        ),
        "multi": LiveCaptureSpec(
            key="multi",
            scenario=_scenario_from_preset("multi"),
            note="Dedicated multitasking surface.",
        ),
        "plan": LiveCaptureSpec(
            key="plan",
            scenario=_scenario_from_preset("plan"),
            note="Dedicated plan surface.",
        ),
        "review": LiveCaptureSpec(
            key="review",
            scenario=_scenario_from_preset("review"),
            note="Dedicated review surface.",
        ),
        "cc": LiveCaptureSpec(
            key="cc",
            scenario=_scenario_from_preset("cc"),
            note="Dedicated command-center surface.",
        ),
        "restore": LiveCaptureSpec(
            key="restore",
            scenario=_scenario_from_preset("restore"),
            note="Dedicated restore browser.",
        ),
        "diff": LiveCaptureSpec(
            key="diff",
            scenario=_scenario_from_preset("diff"),
            note="Dedicated diff surface.",
        ),
        "grep": LiveCaptureSpec(
            key="grep",
            scenario=_scenario_from_preset("grep"),
            note="Dedicated search surface.",
        ),
        "escalation": LiveCaptureSpec(
            key="escalation",
            scenario=_scenario_from_preset("escalation"),
            note="Dedicated escalation surface.",
        ),
        "narrow": LiveCaptureSpec(
            key="narrow",
            scenario=_scenario_from_preset("narrow"),
            note="Narrow-geometry idle state.",
        ),
        "recovery": LiveCaptureSpec(
            key="recovery",
            scenario=_scenario_from_preset("recovery"),
            note="Halted / failure recovery state.",
        ),
        "model_picker_open": LiveCaptureSpec(
            key="model_picker_open",
            scenario=Scenario(
                name="model_picker_open", steps=[0.8, "/model\r", 2.0], graceful_exit=False
            ),
            note="Supplementary picker evidence.",
        ),
        "model_picker_filtered": LiveCaptureSpec(
            key="model_picker_filtered",
            scenario=Scenario(
                name="model_picker_filtered",
                steps=[0.8, "/model\r", 2.0, "cod", 0.6],
                graceful_exit=False,
            ),
            note="Supplementary filtered picker evidence.",
        ),
        "provider_picker_open": LiveCaptureSpec(
            key="provider_picker_open",
            scenario=Scenario(
                name="provider_picker_open", steps=[0.8, "/provider\r", 2.0], graceful_exit=False
            ),
            note="Supplementary picker evidence.",
        ),
        "sessions": LiveCaptureSpec(
            key="sessions",
            scenario=_scenario_from_preset("sessions"),
            note="Session picker overlay.",
        ),
        "palette": LiveCaptureSpec(
            key="palette",
            scenario=_scenario_from_preset("palette"),
            note="Command palette overlay.",
        ),
        "ask_user": LiveCaptureSpec(
            key="ask_user",
            scenario=Scenario(name="ask_user", steps=["__ASK_USER__\r", 0.5, 1.0], graceful_exit=False),
            note="Supplementary ask-user modal evidence.",
        ),
        "warning": LiveCaptureSpec(
            key="warning",
            scenario=Scenario(name="warning", steps=["__WARNING__\r", 0.5, 1.0], graceful_exit=False),
            note="Supplementary warning-banner evidence.",
        ),
    }


def _capture_frame_sequence_asset(
    *,
    stamp: str,
    preset: str,
    output_png: Path,
    output_txt: Path,
    preferred_frames: tuple[str, ...],
) -> Path:
    script = _HERE / "capture_frame_sequence.py"
    subprocess.run(
        [sys.executable, str(script), "--stamp", stamp, "--preset", preset],
        cwd=_AUTOCODE_ROOT,
        check=True,
    )
    scene_dir = _AUTOCODE_ROOT / "docs" / "qa" / "tui-frame-sequences" / stamp / preset
    for prefix in preferred_frames:
        png = scene_dir / f"{prefix}.png"
        txt = scene_dir / f"{prefix}.txt"
        if png.exists() and txt.exists():
            shutil.copy2(png, output_png)
            shutil.copy2(txt, output_txt)
            return output_png
    raise FileNotFoundError(
        f"no preferred frame found for preset {preset!r} in {scene_dir}"
    )


def build_scene_compare_specs() -> list[SceneCompareSpec]:
    return [
        SceneCompareSpec("ready", "01 Ready", "0001", "ready", "direct", "Promoted Track 4 scene."),
        SceneCompareSpec("active", "02 Active", "0002", "active", "direct", "Promoted Track 4 scene."),
        SceneCompareSpec("multi", "03 Multitasking", "0003", "multi", "direct", "Dedicated multitasking surface exists but still needs fidelity refinement."),
        SceneCompareSpec("plan", "04 Plan", "0004", "plan", "direct", "Dedicated plan surface exists; remaining work is visual fidelity."),
        SceneCompareSpec("review", "05 Review", "0005", "review", "direct", "Dedicated review surface exists; remaining work is visual fidelity."),
        SceneCompareSpec("cc", "06 Command center", "0006", "cc", "direct", "Dedicated command-center surface exists; remaining work is visual fidelity."),
        SceneCompareSpec("recovery", "07 Recovery", "0007", "recovery", "direct", "Promoted Track 4 scene."),
        SceneCompareSpec("restore", "08 Restore", "0008", "restore", "direct", "Dedicated restore browser exists; remaining work is visual fidelity."),
        SceneCompareSpec("sessions", "09 Sessions", "0009", "sessions", "direct", "Live session-picker overlay exists; remaining work is visual fidelity."),
        SceneCompareSpec("palette", "10 Palette", "0010", "palette", "direct", "Live palette exists; remaining work is visual fidelity."),
        SceneCompareSpec("diff", "11 Diff focus", "0011", "diff", "direct", "Dedicated diff-focus surface exists; remaining work is visual fidelity."),
        SceneCompareSpec("grep", "12 Search", "0012", "grep", "direct", "Dedicated search surface exists; remaining work is visual fidelity."),
        SceneCompareSpec("escalation", "13 Escalation", "0013", "escalation", "direct", "Dedicated escalation surface exists; remaining work is visual fidelity."),
        SceneCompareSpec("narrow", "14 Narrow", "0014", "narrow", "direct", "Promoted Track 4 scene."),
    ]


def _fit_height(image: Image.Image, target_h: int) -> Image.Image:
    ratio = target_h / image.height
    return image.resize((max(1, int(image.width * ratio)), target_h), Image.LANCZOS)


def _panel(title: str, body: str, *, width: int = 900, height: int = 700) -> Image.Image:
    font = ImageFont.truetype(DEFAULT_FONT, 18)
    small = ImageFont.truetype(DEFAULT_FONT, 14)
    image = Image.new("RGB", (width, height), (24, 24, 24))
    draw = ImageDraw.Draw(image)
    draw.rectangle([0, 0, width - 1, height - 1], outline=(90, 90, 90), width=2)
    draw.rectangle([0, 0, width, 44], fill=(40, 40, 40))
    draw.text((12, 10), title, font=font, fill=(240, 240, 240))
    y = 68
    for line in body.splitlines():
        draw.text((18, y), line, font=small, fill=(205, 205, 205))
        y += 22
    return image


def _make_grid(items: list[tuple[str, Image.Image]], output: Path) -> None:
    if not items:
        return
    small = ImageFont.truetype(DEFAULT_FONT, 14)
    thumbs: list[Image.Image] = []
    for label, image in items:
        thumb = _fit_height(image, 220)
        framed = Image.new("RGB", (thumb.width, thumb.height + 34), (18, 18, 18))
        framed.paste(thumb, (0, 34))
        draw = ImageDraw.Draw(framed)
        draw.text((8, 8), label, font=small, fill=(240, 240, 240))
        thumbs.append(framed)
    cols = 2
    rows = (len(thumbs) + cols - 1) // cols
    width = max(t.width for t in thumbs)
    height = max(t.height for t in thumbs)
    grid = Image.new(
        "RGB",
        (cols * width + (cols + 1) * 16, rows * height + (rows + 1) * 16),
        (10, 10, 10),
    )
    for idx, thumb in enumerate(thumbs):
        x = 16 + (idx % cols) * (width + 16)
        y = 16 + (idx // cols) * (height + 16)
        grid.paste(thumb, (x, y))
    output.parent.mkdir(parents=True, exist_ok=True)
    grid.save(output)


def render_report(stamp: str, asset_root: Path, scene_artifacts: list[SceneArtifact], supplementary: dict[str, Path]) -> str:
    lines = [
        f"# TUI Reference Screenshot Gap Report — {stamp}",
        "",
        "This artifact is a screenshot-first comparison bundle generated from the",
        "current Rust TUI and the exported `tui-references` JPG pages.",
        "",
        "## Outputs",
        "",
        f"- Asset bundle: `{asset_root}`",
        f"- Reference grid: `{asset_root / 'reference_grid.png'}`",
        f"- Live grid: `{asset_root / 'live_grid.png'}`",
        "",
        "## Scene Table",
        "",
        "| Scene | Reference | Live capture | Mode | Comparison sheet | Note |",
        "|---|---|---|---|---|---|",
    ]
    for artifact in scene_artifacts:
        live = str(artifact.live_path) if artifact.live_path else "(none)"
        lines.append(
            f"| `{artifact.spec.scene_id}` | `{artifact.reference_path}` | `{live}` | "
            f"`{artifact.spec.capture_mode}` | `{artifact.compare_path}` | {artifact.spec.note} |"
        )
    lines.extend(
        [
            "",
            "## System-feature note",
            "",
            "Some high-value scenes are not just frontend layout problems.",
            "Planning, restore/checkpoint flow, task/todo visibility, subagent activity,",
            "review/diff, and permission escalation need benchmark-driven or other mid-run",
            "capture paths. Use `capture_frame_sequence.py` when a final-state screenshot",
            "would miss the actual interactive surface.",
            "",
            "## Supplementary Live Captures",
            "",
            "| Capture | Path |",
            "|---|---|",
        ]
    )
    for key, path in supplementary.items():
        lines.append(f"| `{key}` | `{path}` |")
    lines.extend(
        [
            "",
            "## Re-run",
            "",
            "```bash",
            "make tui-reference-gap",
            "```",
            "",
            "This command regenerates the full bundle with a new timestamp.",
        ]
    )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a screenshot-first TUI reference gap report")
    parser.add_argument("--stamp", default="", help="Optional timestamp override")
    args = parser.parse_args(argv)

    stamp = args.stamp or datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    asset_root = ASSET_ROOT / stamp
    live_dir = asset_root / "live"
    compare_dir = asset_root / "compare"
    live_dir.mkdir(parents=True, exist_ok=True)
    compare_dir.mkdir(parents=True, exist_ok=True)

    binary = resolve_tui_binary()
    if not binary.is_file():
        print(f"ERROR: TUI binary not found at {binary}")
        return 2

    mock_backend = _AUTOCODE_ROOT / "tests" / "pty" / "mock_backend.py"
    env_extra = {
        "AUTOCODE_PYTHON_CMD": str(mock_backend),
        "AUTOCODE_MOCK_SUPPRESS_STARTUP_WARNING": "1",
    }

    live_specs = build_live_capture_specs()
    live_outputs: dict[str, Path] = {}
    for spec in live_specs.values():
        png_path = live_dir / f"{spec.key}.png"
        txt_path = live_dir / f"{spec.key}.txt"
        if spec.key == "active":
            live_outputs[spec.key] = _capture_frame_sequence_asset(
                stamp=stamp,
                preset="active",
                output_png=png_path,
                output_txt=txt_path,
                preferred_frames=("02-sleep", "01-input", "03-final"),
            )
            continue
        ansi = capture_scenario(binary, spec.scenario, env_extra=env_extra)
        screen = feed_ansi_to_screen(
            ansi,
            columns=spec.scenario.columns,
            lines=spec.scenario.lines,
        )
        render_screen_to_png(screen, png_path)
        txt_path.write_text("\n".join(screen.display) + "\n", encoding="utf-8")
        live_outputs[spec.key] = png_path

    scene_artifacts: list[SceneArtifact] = []
    compare_font = ImageFont.truetype(DEFAULT_FONT, 18)
    small = ImageFont.truetype(DEFAULT_FONT, 14)
    for spec in build_scene_compare_specs():
        reference_path = REFERENCE_DIR / f"autocode_tui_mockup_pages-to-jpg-{spec.reference_page}.jpg"
        reference_image = Image.open(reference_path).convert("RGB")
        if spec.live_key is not None:
            live_path = live_outputs[spec.live_key]
            live_image = Image.open(live_path).convert("RGB")
        else:
            live_path = None
            live_image = _panel(
                "No deterministic live capture",
                f"Scene: {spec.scene_id}\n{spec.note}",
            )

        target_h = max(reference_image.height, live_image.height, 700)
        ref_fit = _fit_height(reference_image, target_h)
        live_fit = _fit_height(live_image, target_h)
        canvas = Image.new(
            "RGB",
            (ref_fit.width + live_fit.width + 60, target_h + 80),
            (12, 12, 12),
        )
        draw = ImageDraw.Draw(canvas)
        draw.text((20, 20), f"{spec.label} ({spec.scene_id})", font=compare_font, fill=(245, 245, 245))
        draw.text((20, 50), "Reference", font=small, fill=(180, 180, 180))
        draw.text((ref_fit.width + 40, 50), "Live capture", font=small, fill=(180, 180, 180))
        canvas.paste(ref_fit, (20, 80))
        canvas.paste(live_fit, (ref_fit.width + 40, 80))
        compare_path = compare_dir / f"{spec.scene_id}.png"
        canvas.save(compare_path)
        scene_artifacts.append(
            SceneArtifact(
                spec=spec,
                reference_path=reference_path,
                live_path=live_path,
                compare_path=compare_path,
            )
        )

    reference_items = []
    for spec in build_scene_compare_specs():
        ref_image = Image.open(
            REFERENCE_DIR / f"autocode_tui_mockup_pages-to-jpg-{spec.reference_page}.jpg"
        ).convert("RGB")
        reference_items.append((spec.scene_id, ref_image))
    _make_grid(reference_items, asset_root / "reference_grid.png")

    supplementary_keys = supplementary_live_keys()
    live_items = [(key, Image.open(live_outputs[key]).convert("RGB")) for key in supplementary_keys]
    _make_grid(live_items, asset_root / "live_grid.png")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    artifact_path = RESULTS_DIR / f"{stamp}-tui-reference-gap.md"
    report = render_report(
        stamp,
        asset_root,
        scene_artifacts,
        {key: live_outputs[key] for key in supplementary_keys},
    )
    artifact_path.write_text(report, encoding="utf-8")
    print(artifact_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
