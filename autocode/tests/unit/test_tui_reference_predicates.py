"""Unit tests for ``autocode/tests/tui-references/predicates.py``.

The live PTY tests in ``tests/tui-references/test_reference_scenes.py``
exercise the whole pipeline end-to-end and are xfail'd against the current
Go TUI implementation (design-target vs shipped UI — see Entry 1190). These
unit tests cover the predicate helpers in isolation so regressions in the
predicate logic itself can be caught without standing up a PTY.

Stdlib-only.
"""
from __future__ import annotations

import importlib.util
import sys
import textwrap
from pathlib import Path

import pytest

_MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "tests"
    / "tui-references"
    / "predicates.py"
)


def _load_module():
    name = "autocode_tui_references_predicates_unit"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, _MODULE_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def pm():
    return _load_module()


# ----------------------------------------------------- signal-token extraction

def test_derive_signal_tokens_strips_global_words(pm):
    anchors = [
        "sonnet-4.7 · think(med) · tasks:6 · sandbox:local · Recovery halted",
    ]
    tokens = pm._derive_signal_tokens(anchors)
    # Global tokens must be filtered out.
    assert "sonnet-4.7" not in tokens
    assert "tasks:6" not in tokens
    # Discriminating tokens must be kept.
    assert any(t.lower() == "recovery" for t in tokens)


def test_derive_signal_tokens_dedupes(pm):
    anchors = ["foo foo bar bar foo baz"]
    tokens = pm._derive_signal_tokens(anchors)
    assert len(tokens) == len(set(tokens))


def test_derive_signal_tokens_respects_cap(pm):
    # Craft 40 unique tokens; the helper caps at 16.
    anchors = [" ".join(f"unique{i:02d}more" for i in range(40))]
    tokens = pm._derive_signal_tokens(anchors)
    assert len(tokens) == 16


def test_derive_signal_tokens_drops_oversize_tokens(pm):
    anchors = ["short_one " + ("x" * 60) + " other"]
    tokens = pm._derive_signal_tokens(anchors)
    assert all(len(t) <= 40 for t in tokens)


# --------------------------------------------------------- structural helpers

def test_top_strip_returns_requested_rows(pm):
    text = "\n".join(f"row{i}" for i in range(10))
    assert pm._top_strip(text, rows=3) == "row0\nrow1\nrow2"


def test_bottom_strip_returns_tail_rows(pm):
    text = "\n".join(f"row{i}" for i in range(10))
    assert pm._bottom_strip(text, rows=2) == "row8\nrow9"


def test_nonempty_rows_counts_stripped_content(pm):
    text = "alpha\n   \n\nbeta\n gamma \n\n"
    assert pm._nonempty_rows(text) == 3


# ------------------------------------------------------------ HUD / composer

def test_hud_present_passes_when_tokens_visible(pm):
    text = "header · tasks:6 · agents:2 · sandbox:local\nbody\nmore body"
    result = pm._pred_hud_present(text)
    assert result.verdict is pm.ReferenceVerdict.PASS


def test_hud_present_fails_when_only_welcome_banner(pm):
    text = "AutoCode — Edge-native AI coding assistant\nType /help for commands..."
    result = pm._pred_hud_present(text)
    assert result.verdict is pm.ReferenceVerdict.FAIL


def test_composer_present_passes_on_composer_marker(pm):
    text = "\n".join([""] * 20 + ["│ ❯ │ type here │"])
    result = pm._pred_composer_present(text)
    assert result.verdict is pm.ReferenceVerdict.PASS


def test_composer_present_passes_on_ask_prompt(pm):
    text = "\n".join([""] * 20 + ["❯ Ask AutoCode anything"])
    result = pm._pred_composer_present(text)
    assert result.verdict is pm.ReferenceVerdict.PASS


def test_composer_present_fails_on_bare_output(pm):
    text = "\n".join(["Hello"] * 25)
    result = pm._pred_composer_present(text)
    assert result.verdict is pm.ReferenceVerdict.FAIL


def test_keybind_footer_present_detects_ctrl_esc(pm):
    text = "\n".join([""] * 20 + ["Ctrl+Enter send · Esc interrupt"])
    result = pm._pred_keybind_footer_present(text)
    assert result.verdict is pm.ReferenceVerdict.PASS


def test_keybind_footer_missing_when_absent(pm):
    text = "\n".join([""] * 20 + ["plain status line"])
    result = pm._pred_keybind_footer_present(text)
    assert result.verdict is pm.ReferenceVerdict.FAIL


# ------------------------------------------------------- scene-specific

def test_recovery_cards_requires_four_of_six_labels(pm):
    text_full = "retry · inspect · restore · rewind · compact · return to planning"
    text_partial = "retry · inspect · restore · rewind"
    text_two = "retry · inspect"
    assert pm._pred_scene_recovery_cards(text_full).verdict is pm.ReferenceVerdict.PASS
    assert pm._pred_scene_recovery_cards(text_partial).verdict is pm.ReferenceVerdict.PASS
    assert pm._pred_scene_recovery_cards(text_two).verdict is pm.ReferenceVerdict.FAIL


def test_narrow_layout_fits_within_budget(pm):
    ok = "short line\nalso short"
    overflow = "X" * 80 + "\nshort"
    r_ok = pm._pred_scene_narrow_layout(ok, cols=68)
    r_over = pm._pred_scene_narrow_layout(overflow, cols=68)
    assert r_ok.verdict is pm.ReferenceVerdict.PASS
    assert r_over.verdict is pm.ReferenceVerdict.FAIL


def test_active_turn_indicator_detects_working(pm):
    pass_v = pm._pred_scene_active_streaming("● working on parser").verdict
    fail_v = pm._pred_scene_active_streaming("plain output").verdict
    assert pass_v is pm.ReferenceVerdict.PASS
    assert fail_v is pm.ReferenceVerdict.FAIL


# -------------------------------------------------- full orchestration path

def _make_scene_dict(**overrides):
    base = {
        "scene_id": "ready",
        "label": "01 Ready",
        "page_number": 1,
        "populated": True,
        "anchors": [],
        "region_classes": ["hud", "composer-wrap"],
        "class_counts": {},
    }
    base.update(overrides)
    return base


def test_run_scene_predicates_stubbed_scene_short_circuits(pm):
    scene = _make_scene_dict(scene_id="grep", populated=False)
    report = pm.run_scene_predicates("whatever", scene, cols=80)
    assert len(report.checks) == 1
    assert report.checks[0].verdict is pm.ReferenceVerdict.NA
    assert report.all_passed  # NA counts as non-failing


def test_run_scene_predicates_includes_recovery_check(pm):
    scene = _make_scene_dict(scene_id="recovery", label="07 Recovery")
    report = pm.run_scene_predicates("text", scene, cols=80)
    names = {c.name for c in report.checks}
    assert "recovery_cards_visible" in names


def test_run_scene_predicates_includes_narrow_check(pm):
    scene = _make_scene_dict(scene_id="narrow", label="14 Narrow")
    report = pm.run_scene_predicates("text", scene, cols=68)
    names = {c.name for c in report.checks}
    assert "narrow_layout_fits" in names


def test_run_scene_predicates_includes_active_check(pm):
    scene = _make_scene_dict(scene_id="active", label="02 Active")
    report = pm.run_scene_predicates("text", scene, cols=160)
    names = {c.name for c in report.checks}
    assert "active_turn_indicator" in names


def test_run_scene_predicates_ready_has_no_scene_specific_check(pm):
    scene = _make_scene_dict(scene_id="ready")
    report = pm.run_scene_predicates("text", scene, cols=160)
    names = {c.name for c in report.checks}
    # ready has no scene-specific predicate in Slice 1.
    assert "recovery_cards_visible" not in names
    assert "active_turn_indicator" not in names
    assert "narrow_layout_fits" not in names


def test_report_failures_lists_only_failing(pm):
    scene = _make_scene_dict()
    report = pm.run_scene_predicates("", scene, cols=160)  # empty → failures
    failing_names = {c.name for c in report.failures()}
    # At least one universal predicate must fail on empty text.
    assert len(failing_names) > 0
    assert not report.all_passed


def test_report_as_dict_is_json_safe(pm):
    import json
    scene = _make_scene_dict(scene_id="narrow", label="14 Narrow")
    report = pm.run_scene_predicates("some text", scene, cols=68)
    blob = report.as_dict()
    # Must round-trip through json without TypeErrors on the enum.
    json.dumps(blob)
    assert blob["scene_id"] == "narrow"
    assert blob["label"] == "14 Narrow"
    assert isinstance(blob["checks"], list)


# --------------------------------------------------- manifest reader round-trip

def test_load_scene_records_reads_our_emitter_output(pm, tmp_path):
    yaml_src = textwrap.dedent(
        """
        # Auto-generated header — ignored by reader
        version: 1
        scene_count: 2
        scenes:
          - scene_id: ready
            label: "01 Ready"
            page_number: 1
            populated: true
            raw_inner_length: 100
            region_classes:
              - hud
              - composer-wrap
            anchors:
              - "some anchor"
              - "another anchor"
            class_counts:
              hud: 1
              composer-wrap: 1
          - scene_id: grep
            label: "12 Search"
            page_number: 12
            populated: false
            raw_inner_length: 50
            region_classes: []
            anchors: []
            class_counts: {}
        """
    ).strip()
    path = tmp_path / "manifest.yaml"
    path.write_text(yaml_src, encoding="utf-8")
    records = pm.load_scene_records(path)
    assert len(records) == 2

    ready = records[0]
    assert ready["scene_id"] == "ready"
    assert ready["label"] == "01 Ready"
    assert ready["page_number"] == 1
    assert ready["populated"] is True
    assert ready["region_classes"] == ["hud", "composer-wrap"]
    assert ready["anchors"] == ["some anchor", "another anchor"]

    grep = records[1]
    assert grep["scene_id"] == "grep"
    assert grep["populated"] is False
    assert grep["anchors"] == []
    assert grep["region_classes"] == []


def test_load_scene_records_round_trips_real_manifest(pm):
    real_manifest = (
        Path(__file__).resolve().parents[2]
        / "tests"
        / "tui-references"
        / "manifest.yaml"
    )
    if not real_manifest.is_file():
        pytest.skip("manifest not generated; run extract_scenes.py first")
    records = pm.load_scene_records(real_manifest)
    assert len(records) == 14
    assert {r["scene_id"] for r in records} >= {
        "ready", "active", "recovery", "narrow"
    }
    populated = {r["scene_id"] for r in records if r["populated"]}
    assert populated == {"ready", "active", "recovery", "narrow"}


# Regression guards: an earlier reader corrupted nested ``class_counts``
# maps into the scene root. These tests pin the fixed behaviour so the
# bug cannot silently return.

def test_load_scene_records_class_counts_is_dict_for_populated_scenes(pm):
    real_manifest = (
        Path(__file__).resolve().parents[2]
        / "tests"
        / "tui-references"
        / "manifest.yaml"
    )
    if not real_manifest.is_file():
        pytest.skip("manifest not generated; run extract_scenes.py first")
    records = pm.load_scene_records(real_manifest)
    populated = [r for r in records if r["populated"]]
    assert populated, "at least one scene must be populated"
    for scene in populated:
        counts = scene["class_counts"]
        assert isinstance(counts, dict), (
            f"{scene['scene_id']} class_counts must be dict, got {type(counts).__name__}"
        )
        assert counts, (
            f"{scene['scene_id']} class_counts must be non-empty for a populated scene"
        )


def test_load_scene_records_does_not_leak_class_count_keys_to_root(pm):
    """The broken reader put keys like ``accept: 1`` onto the scene root."""
    real_manifest = (
        Path(__file__).resolve().parents[2]
        / "tests"
        / "tui-references"
        / "manifest.yaml"
    )
    if not real_manifest.is_file():
        pytest.skip("manifest not generated; run extract_scenes.py first")
    records = pm.load_scene_records(real_manifest)
    expected_scene_keys = {
        "scene_id", "label", "page_number", "populated",
        "raw_inner_length", "region_classes", "anchors", "class_counts",
    }
    for scene in records:
        leaked = set(scene.keys()) - expected_scene_keys
        assert not leaked, (
            f"{scene['scene_id']} has unexpected top-level keys (class_counts "
            f"leak): {sorted(leaked)}"
        )


def test_load_scene_records_preserves_known_class_counts(pm):
    """Well-known class tokens from the extractor must survive the YAML round-trip."""
    real_manifest = (
        Path(__file__).resolve().parents[2]
        / "tests"
        / "tui-references"
        / "manifest.yaml"
    )
    if not real_manifest.is_file():
        pytest.skip("manifest not generated; run extract_scenes.py first")
    records = pm.load_scene_records(real_manifest)
    by_id = {r["scene_id"]: r for r in records}
    # ``composer-wrap`` is present in every MVP scene by the extractor's
    # region-class whitelist and is a known stable anchor.
    for scene_id in ("ready", "active", "recovery", "narrow"):
        counts = by_id[scene_id]["class_counts"]
        assert counts.get("composer-wrap", 0) >= 1, (
            f"{scene_id} should preserve composer-wrap count from extraction; "
            f"got {counts.get('composer-wrap', 0)} — "
            f"class_counts keys: {sorted(counts)[:10]}"
        )


def test_load_scene_records_nested_map_inline_empty_sentinel(pm, tmp_path):
    """Inline ``{}`` sentinel must produce an empty dict, not accidentally
    become a list or swallow subsequent keys."""
    yaml_src = textwrap.dedent(
        """
        version: 1
        scenes:
          - scene_id: stub
            label: "Stub"
            page_number: 99
            populated: false
            region_classes: []
            anchors: []
            class_counts: {}
        """
    ).strip()
    path = tmp_path / "manifest.yaml"
    path.write_text(yaml_src, encoding="utf-8")
    records = pm.load_scene_records(path)
    assert len(records) == 1
    stub = records[0]
    assert stub["class_counts"] == {}
    assert isinstance(stub["class_counts"], dict)
    assert stub["anchors"] == []
    assert stub["region_classes"] == []


def test_capture_sanity_floor_constant_matches_implementation(pm):
    """The threshold constant must be the single source of truth for the
    ``nonempty_row_floor`` predicate — prevents comment/impl drift."""
    # The constant must exist and be an int.
    assert hasattr(pm, "_CAPTURE_SANITY_ROW_FLOOR")
    assert isinstance(pm._CAPTURE_SANITY_ROW_FLOOR, int)
    # Predicate output must reference the constant's value in its detail.
    scene = _make_scene_dict(scene_id="ready")
    text_below = "\n".join(["line"] * (pm._CAPTURE_SANITY_ROW_FLOOR - 1))
    text_at_floor = "\n".join(["line"] * pm._CAPTURE_SANITY_ROW_FLOOR)
    report_below = pm.run_scene_predicates(text_below, scene, cols=160)
    report_at = pm.run_scene_predicates(text_at_floor, scene, cols=160)
    floor_below = next(c for c in report_below.checks if c.name == "nonempty_row_floor")
    floor_at = next(c for c in report_at.checks if c.name == "nonempty_row_floor")
    assert floor_below.verdict is pm.ReferenceVerdict.FAIL
    assert floor_at.verdict is pm.ReferenceVerdict.PASS
    assert str(pm._CAPTURE_SANITY_ROW_FLOOR) in floor_at.detail
