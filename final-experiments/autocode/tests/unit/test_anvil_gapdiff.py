"""Tests for the copycat gap-diff (target census vs AutoCode manifest).

Per PLAN_05 §2.3 step 2: diff each reference's capability set against AutoCode's
manifest, output the gap list. The diff must (a) treat differently-named but
equivalent capabilities as *present* (aliases), (b) ignore vendor-specific noise,
and (c) classify true gaps for clean-room suitability.
"""

from __future__ import annotations

from autocode.anvil.census import Capability, Census
from autocode.anvil.gapdiff import GapReport, gap_diff
from autocode.anvil.manifest import autocode_manifest
from autocode.anvil.targets import collect_puku_census


def _cap(cap_id: str, *surface: str, kind: str = "flag") -> Capability:
    return Capability(id=cap_id, kind=kind, surface=tuple(surface) or (cap_id,))


def _manifest(*caps: Capability) -> Census:
    return Census(target="autocode", source="test", capabilities=tuple(caps))


def _census(*caps: Capability) -> Census:
    return Census(target="puku-cli", source="test", capabilities=tuple(caps))


def test_missing_capability_is_a_gap() -> None:
    target = _census(_cap("flag:max-budget-usd", "--max-budget-usd"))
    report = gap_diff(target, _manifest(_cap("flag:json", "--json")))
    assert isinstance(report, GapReport)
    assert "flag:max-budget-usd" in report.gap_ids()


def test_same_id_is_present_not_a_gap() -> None:
    target = _census(_cap("flag:verbose", "--verbose"))
    report = gap_diff(target, _manifest(_cap("flag:verbose", "--verbose", "-v")))
    assert "flag:verbose" not in report.gap_ids()
    assert any(p.capability.id == "flag:verbose" for p in report.present)


def test_shared_surface_token_counts_as_present() -> None:
    # Different canonical ids but a shared long flag -> present.
    target = _census(_cap("flag:allowedTools", "--allowedTools", "--allowed-tools"))
    report = gap_diff(target, _manifest(_cap("flag:allowed-tools", "--allowed-tools")))
    assert "flag:allowedTools" not in report.gap_ids()


def test_alias_maps_to_existing_autocode_capability() -> None:
    # puku --output-format stream-json ≈ autocode `exec --json` (NDJSON).
    target = _census(_cap("flag:output-format", "--output-format"))
    report = gap_diff(target, _manifest(_cap("flag:json", "--json")))
    assert "flag:output-format" not in report.gap_ids()
    present = next(p for p in report.present if p.capability.id == "flag:output-format")
    assert present.via == "alias"
    assert present.autocode_id == "flag:json"


def test_vendor_noise_is_ignored_not_a_gap() -> None:
    target = _census(
        _cap("flag:help", "--help", "-h"),
        _cap("flag:version", "--version", "-v"),
        _cap("flag:chrome", "--chrome"),
    )
    report = gap_diff(target, _manifest())
    assert report.gap_ids() == set()
    assert {c.id for c in report.ignored} >= {"flag:help", "flag:version", "flag:chrome"}


def test_budget_gap_is_classified_cleanroom_suitable() -> None:
    target = _census(_cap("flag:max-budget-usd", "--max-budget-usd"))
    report = gap_diff(target, _manifest())
    gap = next(g for g in report.gaps if g.capability.id == "flag:max-budget-usd")
    assert gap.category == "budget"
    assert gap.cleanroom_suitable is True
    assert gap.rationale


def test_landing_the_feature_closes_the_gap() -> None:
    target = _census(_cap("flag:max-budget-usd", "--max-budget-usd"))
    # Simulate the post-promotion manifest where AutoCode now exposes the flag.
    after = _manifest(_cap("flag:max-budget-usd", "--max-budget-usd"))
    report = gap_diff(target, after)
    assert "flag:max-budget-usd" not in report.gap_ids()


def test_gaps_are_rank_sorted_with_missing_capability_bias() -> None:
    # A missing-capability gap (category "tools") must outrank an equal-frequency
    # provider gap (not a missing-capability category) because of the §3.3 ×3 bias,
    # even though the provider id sorts earlier alphabetically.
    classification = {
        "flag:provider": ("provider", False, "per-call provider override; defer"),
        "flag:tools": ("tools", False, "restrict the built-in tool set; missing capability"),
    }
    target = _census(
        _cap("flag:provider", "--provider"),
        _cap("flag:tools", "--tools"),
    )
    report = gap_diff(target, _manifest(), classification=classification)
    ranks = [g.rank for g in report.gaps]
    # Output is sorted by rank, descending.
    assert ranks == sorted(ranks, reverse=True)
    # And the missing-capability gap (×3 bias) is ranked first.
    assert report.gaps[0].capability.id == "flag:tools"
    assert report.gaps[0].rank > report.gaps[1].rank


def test_rank_uses_frequency_from_command_count() -> None:
    # A flag exposed on more commands has higher frequency -> higher rank, all
    # else equal (mirrors taxonomy's frequency × severity × bias).
    classification = {
        "flag:a": ("provider", False, "x"),
        "flag:b": ("provider", False, "y"),
    }
    cap_a = Capability(id="flag:a", kind="flag", surface=("--a",), metadata={"commands": ["exec"]})
    cap_b = Capability(
        id="flag:b", kind="flag", surface=("--b",),
        metadata={"commands": ["exec", "run", "chat"]},
    )
    report = gap_diff(_census(cap_a, cap_b), _manifest(), classification=classification)
    by_id = {g.capability.id: g for g in report.gaps}
    assert by_id["flag:b"].rank > by_id["flag:a"].rank
    # Higher rank sorts first.
    assert report.gaps[0].capability.id == "flag:b"


def test_real_puku_vs_real_autocode_surfaces_headline_gaps() -> None:
    # The end-to-end shape: real snapshot census vs real AutoCode manifest.
    census = collect_puku_census(runner=lambda args: None)  # snapshot, deterministic
    report = gap_diff(census, autocode_manifest())
    gap_ids = report.gap_ids()
    present_ids = {p.capability.id for p in report.present}

    # These two puku-cli features were copied into AutoCode (clean-room) by this
    # very change, so the loop has closed: they are now PRESENT, not gaps.
    assert "flag:max-budget-usd" in present_ids
    assert "flag:max-budget-usd" not in gap_ids
    assert "flag:permission-mode" in present_ids
    assert "flag:permission-mode" not in gap_ids

    # All five curated clean-room-suitable puku-cli features have now been copied
    # into AutoCode, so they are present (gap closed), not gaps.
    for copied in (
        "flag:system-prompt",
        "flag:append-system-prompt",
        "flag:add-dir",
    ):
        assert copied in present_ids, copied
        assert copied not in gap_ids, copied

    # Gaps still exist (provider/effort/etc.), but none are clean-room-suitable
    # anymore — every curated-suitable capability has been promoted.
    assert len(report.gaps) > 0
    assert report.suitable_gaps() == []
