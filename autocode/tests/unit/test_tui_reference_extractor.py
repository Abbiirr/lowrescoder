"""Unit tests for the tui-references scene extractor.

Locks the contract between the design bundle
(``tui-references/AutoCode TUI _standalone_.html``) and the reference-driven
parity tests: 14 scenes, stable ids, label + page-number extraction, and
region-class detection for the 4 MVP scenes.

Stdlib-only.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "tests"
    / "tui-references"
    / "extract_scenes.py"
)

_HTML_PATH = (
    Path(__file__).resolve().parents[3]
    / "tui-references"
    / "AutoCode TUI _standalone_.html"
)


def _load_module():
    import sys
    mod_name = "autocode_tui_references_extract_scenes"
    if mod_name in sys.modules:
        return sys.modules[mod_name]
    spec = importlib.util.spec_from_file_location(mod_name, _MODULE_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[mod_name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def scenes():
    if not _HTML_PATH.is_file():
        pytest.skip(f"HTML bundle not present at {_HTML_PATH}")
    es = _load_module()
    return es.extract_scenes(_HTML_PATH)


@pytest.fixture(scope="module")
def module():
    return _load_module()


# ------------------------------------------------------------------ structural

def test_all_fourteen_scenes_extracted(scenes):
    assert len(scenes) == 14


def test_scene_ids_match_bundle(scenes):
    ids = {s.scene_id for s in scenes}
    expected = {
        "ready", "active", "multi", "plan", "review", "cc", "recovery",
        "restore", "sessions", "palette", "diff", "grep", "escalation",
        "narrow",
    }
    assert ids == expected


def test_mvp_scenes_are_populated(scenes):
    mvp = {"ready", "active", "recovery", "narrow"}
    populated = {s.scene_id for s in scenes if s.populated}
    assert populated == mvp


def test_non_mvp_scenes_are_stubbed(scenes):
    non_mvp = {s.scene_id for s in scenes if not s.populated}
    assert non_mvp == {
        "multi", "plan", "review", "cc", "restore",
        "sessions", "palette", "diff", "grep", "escalation",
    }


# ------------------------------------------------------------------ label + order

def test_labels_present_on_every_scene(scenes):
    missing = [s.scene_id for s in scenes if not s.label]
    assert missing == [], f"scenes missing label: {missing}"


def test_page_numbers_parsed_for_mvp(scenes):
    by_id = {s.scene_id: s for s in scenes}
    assert by_id["ready"].page_number == 1
    assert by_id["active"].page_number == 2
    assert by_id["recovery"].page_number == 7
    assert by_id["narrow"].page_number == 14


def test_scenes_sorted_by_page_then_id(scenes):
    pages = [(s.page_number, s.scene_id) for s in scenes]
    assert pages == sorted(pages)


# ------------------------------------------------------------------ region detection

def test_mvp_scenes_have_expected_regions(scenes):
    by_id = {s.scene_id: s for s in scenes}
    # Every MVP frame must include the top HUD strip + the composer wrapper.
    for scene_id in ("ready", "active", "recovery", "narrow"):
        regions = set(by_id[scene_id].region_classes)
        assert "hud" in regions, f"{scene_id} missing hud"
        assert "composer-wrap" in regions, f"{scene_id} missing composer-wrap"


def test_active_scene_has_tool_and_diff(scenes):
    active = next(s for s in scenes if s.scene_id == "active")
    regions = set(active.region_classes)
    # Page 02 shows a streaming tool-chain with inline diff hunks.
    assert "tool" in regions
    assert "diff" in regions


def test_every_scene_captures_anchor_text(scenes):
    # Populated OR stubbed, every reference scene contains visible text —
    # even the nav/toc rows. Zero anchors means the parser lost the subtree.
    for s in scenes:
        assert s.anchors, f"{s.scene_id} has no anchor text"


# ------------------------------------------------------------------ bundle decode

def test_bundle_loader_returns_expected_payload(module):
    if not _HTML_PATH.is_file():
        pytest.skip("HTML bundle not present")
    bundle = module.load_bundle(_HTML_PATH)
    assert bundle.manifest
    assert isinstance(bundle.template, str)
    assert bundle.template.count('<template id="t-') == 14


def test_manifest_entries_declare_fonts(module):
    if not _HTML_PATH.is_file():
        pytest.skip("HTML bundle not present")
    bundle = module.load_bundle(_HTML_PATH)
    mimes = {entry.get("mime") for entry in bundle.manifest.values()}
    # Tokyo Night bundle embeds JetBrains Mono + Inter as woff2 assets.
    assert "font/woff2" in mimes
