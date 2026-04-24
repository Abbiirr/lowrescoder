from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
TUI_REFERENCES_ROOT = REPO_ROOT / "autocode" / "tests" / "tui-references"
GAP_REPORT_PATH = TUI_REFERENCES_ROOT / "build_visual_gap_report.py"
FRAME_CAPTURE_PATH = TUI_REFERENCES_ROOT / "capture_frame_sequence.py"
PRESETS_PATH = TUI_REFERENCES_ROOT / "scene_presets.py"
MATRIX_CAPTURE_PATH = TUI_REFERENCES_ROOT / "capture_reference_scene_matrix.py"
ALL_SCENE_IDS = {
    "ready",
    "active",
    "multi",
    "plan",
    "review",
    "cc",
    "recovery",
    "restore",
    "sessions",
    "palette",
    "diff",
    "grep",
    "escalation",
    "narrow",
}


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_scene_compare_specs_cover_all_reference_scenes() -> None:
    mod = _load_module("tui_ref_gap_report_mod", GAP_REPORT_PATH)

    specs = mod.build_scene_compare_specs()
    scene_ids = [spec.scene_id for spec in specs]

    assert len(specs) == 14
    assert len(scene_ids) == len(set(scene_ids))
    assert ALL_SCENE_IDS == set(scene_ids)

    mode_counts = {}
    for spec in specs:
        mode_counts[spec.capture_mode] = mode_counts.get(spec.capture_mode, 0) + 1
    assert mode_counts == {"direct": 14}


def test_gap_report_helpers_expose_system_feature_support() -> None:
    mod = _load_module("tui_ref_gap_report_mod_keys", GAP_REPORT_PATH)

    supplementary = mod.supplementary_live_keys()
    assert "sessions" in supplementary
    assert "palette" in supplementary
    assert "model_picker_open" in supplementary


def test_scene_presets_cover_all_reference_scenes() -> None:
    mod = _load_module("tui_ref_scene_presets_mod", PRESETS_PATH)

    presets = mod.scene_presets()
    assert len(presets) == 14
    assert ALL_SCENE_IDS == set(presets)

    mode_counts = {}
    for preset in presets.values():
        mode_counts[preset.capture_mode] = mode_counts.get(preset.capture_mode, 0) + 1
    assert mode_counts == {"direct": 14}

    assert presets["active"].steps[0].endswith("\r")
    assert presets["active"].capture_mode == "direct"
    assert presets["plan"].runnable is True


def test_capture_matrix_attempts_cover_all_reference_scenes() -> None:
    mod = _load_module("tui_ref_scene_matrix_mod", MATRIX_CAPTURE_PATH)

    attempts = mod.scene_attempts()
    scene_ids = [attempt.scene_id for attempt in attempts]
    assert len(attempts) == 14
    assert ALL_SCENE_IDS == set(scene_ids)

    kind_counts = {}
    for attempt in attempts:
        kind_counts[attempt.result_kind] = kind_counts.get(attempt.result_kind, 0) + 1
    assert kind_counts == {"direct": 14}

    escalation = next(item for item in attempts if item.scene_id == "escalation")
    assert escalation.trigger == "preset:escalation"


def test_parse_steps_literal_accepts_strings_and_numbers() -> None:
    mod = _load_module("tui_ref_frame_capture_mod", FRAME_CAPTURE_PATH)

    steps = mod.parse_steps_literal(r"""[0.8, "/sessions\r", 2]""")
    assert steps == [0.8, "/sessions\r", 2.0]


def test_parse_steps_literal_rejects_non_list() -> None:
    mod = _load_module("tui_ref_frame_capture_mod_bad", FRAME_CAPTURE_PATH)

    with pytest.raises(ValueError, match="list"):
        mod.parse_steps_literal("'hello'")
