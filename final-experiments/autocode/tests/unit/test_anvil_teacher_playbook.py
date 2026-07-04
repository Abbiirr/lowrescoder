"""Tests for the ACE playbook store (Curator / Pruner / Loader, §4)."""

from __future__ import annotations

from pathlib import Path

import pytest

from autocode.anvil.teacher.playbook import PlaybookStore, PruneRegressionError
from autocode.anvil.teacher.schemas import PlaybookDelta, Provenance


def _delta(
    delta_id: str, rule: str, *, trigger: str, lang: str = "python", evid: str = "tj_1"
) -> PlaybookDelta:
    return PlaybookDelta(
        delta_id=delta_id,
        trajectory_id=evid,
        verdict="fail",
        root_cause_class="tool.missing_capability",
        trigger=trigger,
        observation="escalated L2->L4",
        rule=rule,
        evidence_trajectory=evid,
        language=lang,
        created="2026-06-21",
        provenance=Provenance(teacher_model="coding", anvil_version="0.1.0"),
    )


def test_append_delta_is_append_only(tmp_path: Path) -> None:
    store = PlaybookStore(tmp_path)
    store.append_delta(_delta("pd_1", "prefer L2 retrieval", trigger="callers-of X"))
    store.append_delta(_delta("pd_2", "second pass before escalating", trigger="callees-of Y"))
    deltas = store.read_deltas("python")
    assert [d.delta_id for d in deltas] == ["pd_1", "pd_2"]
    # JSONL has exactly two lines — nothing was rewritten/dropped.
    assert store.deltas_path("python").read_text().strip().count("\n") == 1


def test_meta_tracks_delta_count(tmp_path: Path) -> None:
    store = PlaybookStore(tmp_path)
    store.append_delta(_delta("pd_1", "r1", trigger="t1"))
    store.append_delta(_delta("pd_2", "r2", trigger="t2"))
    meta = store._load_meta()
    assert meta["languages"]["python"]["delta_count"] == 2


def test_loader_returns_delta_rules_before_prune(tmp_path: Path) -> None:
    store = PlaybookStore(tmp_path)
    store.append_delta(_delta("pd_1", "prefer L2 retrieval", trigger="callers-of X"))
    rules = store.load_rules("python")
    assert rules == ["prefer L2 retrieval"]


def test_pruner_merges_overlapping_same_trigger(tmp_path: Path) -> None:
    store = PlaybookStore(tmp_path)
    # Two deltas, same class + same (normalized) trigger => one Master Rule.
    store.append_delta(_delta("pd_1", "prefer L2 retrieval", trigger="callers-of X across files"))
    store.append_delta(
        _delta(
            "pd_2",
            "prefer L2 retrieval first, escalate after a 2nd anchor",
            trigger="Callers-of X  across   files",
        )
    )
    result = store.prune("python")
    assert result.deltas_in == 2
    assert result.rules_out == 1
    mr = result.merged[0]
    assert mr.support == 2
    # Anti-brevity: the longer, more-detailed phrasing is kept as canonical.
    assert "escalate after" in mr.rule


def test_pruner_keeps_distinct_triggers_separate(tmp_path: Path) -> None:
    store = PlaybookStore(tmp_path)
    store.append_delta(_delta("pd_1", "r1", trigger="callers-of X"))
    store.append_delta(_delta("pd_2", "r2", trigger="stale context after edit"))
    result = store.prune("python")
    assert result.rules_out == 2


def test_loader_prefers_master_rules_after_prune(tmp_path: Path) -> None:
    store = PlaybookStore(tmp_path)
    store.append_delta(_delta("pd_1", "prefer L2 retrieval", trigger="callers-of X"))
    store.append_delta(_delta("pd_2", "prefer L2 retrieval", trigger="callers-of X"))
    store.prune("python")
    rules = store.load_rules("python")
    assert rules == ["prefer L2 retrieval"]  # merged, deduped


def test_deltas_survive_prune(tmp_path: Path) -> None:
    store = PlaybookStore(tmp_path)
    store.append_delta(_delta("pd_1", "r1", trigger="t1"))
    store.prune("python")
    # Pruning never deletes the append-only source of truth.
    assert len(store.read_deltas("python")) == 1


def test_md_view_regenerated_and_human_readable(tmp_path: Path) -> None:
    store = PlaybookStore(tmp_path)
    store.append_delta(_delta("pd_1", "prefer L2 retrieval", trigger="callers-of X"))
    md = store.md_path("python").read_text()
    assert "# Playbook: python" in md
    assert "## Master Rules" in md
    assert "## Deltas (append-only)" in md
    assert "pd_1" in md


def test_render_prompt_block(tmp_path: Path) -> None:
    store = PlaybookStore(tmp_path)
    store.append_delta(_delta("pd_1", "prefer L2 retrieval", trigger="callers-of X"))
    block = store.render_prompt_block("python")
    assert "Playbook (python)" in block
    assert "prefer L2 retrieval" in block
    assert store.render_prompt_block("rust") == ""  # no rules for an unseen language


def test_per_language_isolation(tmp_path: Path) -> None:
    store = PlaybookStore(tmp_path)
    store.append_delta(_delta("pd_1", "py rule", trigger="t", lang="python"))
    store.append_delta(_delta("pd_2", "rs rule", trigger="t", lang="rust"))
    assert store.load_rules("python") == ["py rule"]
    assert store.load_rules("rust") == ["rs rule"]


# --- A.1 — prediction-gated Pruner merge (06 §6.3) ------------------------- #


def test_prune_eval_gate_blocks_regressing_merge(tmp_path: Path) -> None:
    # A gate that reports a pass@1 regression refuses the merge and writes nothing.
    store = PlaybookStore(tmp_path)
    store.append_delta(_delta("pd_1", "prefer L2 retrieval", trigger="callers-of X"))
    with pytest.raises(PruneRegressionError, match="pass@1"):
        store.prune("python", eval_gate=lambda before, after: False)
    # No Master Rules were committed; the loader still falls back to the deltas.
    assert store.master_rules("python") == []
    assert store.load_rules("python") == ["prefer L2 retrieval"]
    # And the deltas are untouched (the merge is reversible).
    assert len(store.read_deltas("python")) == 1


def test_prune_eval_gate_allows_safe_merge(tmp_path: Path) -> None:
    store = PlaybookStore(tmp_path)
    store.append_delta(_delta("pd_1", "prefer L2 retrieval", trigger="callers-of X"))
    store.append_delta(_delta("pd_2", "prefer L2 retrieval", trigger="callers-of X"))
    result = store.prune("python", eval_gate=lambda before, after: True)
    assert result.rules_out == 1
    assert store.master_rules("python")


def test_coverage_gate_refuses_class_coverage_loss(tmp_path: Path) -> None:
    # The default CLI gate refuses a merge that drops a previously-covered class.
    from autocode.anvil.teacher.cli import _coverage_eval_gate

    store = PlaybookStore(tmp_path)
    store.append_delta(_delta("pd_1", "r1", trigger="t1"))
    store.prune("python")  # first prune: establishes coverage of the class
    before = store.master_rules("python")
    assert before
    # A candidate merge that drops all rules erases the class -> refused.
    assert _coverage_eval_gate(before, []) is False
    # A candidate that keeps the same classes is allowed.
    assert _coverage_eval_gate(before, before) is True
