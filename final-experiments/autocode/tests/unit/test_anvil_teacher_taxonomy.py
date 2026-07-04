"""Tests for the root-cause taxonomy and the cluster-ranking rule (§3.1/§3.3)."""

from __future__ import annotations

from autocode.anvil.teacher.taxonomy import (
    FAILURE_TABLE,
    RootCauseClass,
    cluster_rank,
    fix_info,
    is_known_class,
    rank_clusters,
)


def test_all_ten_classes_present_in_table() -> None:
    expected = {
        "reasoning.wrong_plan",
        "reasoning.early_stop",
        "retrieval.miss",
        "retrieval.stale_context",
        "tool.wrong_choice",
        "tool.bad_args",
        "tool.missing_capability",
        "context.overflow",
        "verify.no_self_check",
        "style.weak_output",
    }
    assert set(FAILURE_TABLE) == expected


def test_missing_capability_targets_tool_implementation_tier1() -> None:
    info = fix_info(RootCauseClass.TOOL_MISSING_CAPABILITY.value)
    assert info is not None
    assert info.fix_tier == 1
    assert info.component_kind == "tool_implementation"


def test_is_known_class_rejects_sentinel() -> None:
    assert is_known_class("tool.missing_capability")
    assert not is_known_class("")  # the NONE sentinel is not a real class


def test_cluster_rank_triples_missing_capability() -> None:
    base = cluster_rank(frequency=3, severity=1.0, is_tool_missing_capability=False)
    boosted = cluster_rank(frequency=3, severity=1.0, is_tool_missing_capability=True)
    assert base == 3.0
    assert boosted == 9.0  # ×(1 + 2)


def test_missing_capability_cluster_outranks_larger_style_cluster() -> None:
    # §3.3 worked claim: 3 missing-capability failures outrank 6 style failures.
    clusters = [
        {"class": "style.weak_output", "frequency": 6, "severity": 1.0},
        {"class": "tool.missing_capability", "frequency": 3, "severity": 1.0},
    ]
    ranked = rank_clusters(clusters)
    assert ranked[0]["class"] == "tool.missing_capability"
    assert ranked[0]["rank"] == 9.0
    assert ranked[1]["rank"] == 6.0
