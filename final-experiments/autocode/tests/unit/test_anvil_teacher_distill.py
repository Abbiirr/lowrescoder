"""Tests for PLAN_04 §7 Phase 3 — G5 distiller (teacher/distill.py).

Verifies the distiller produces the layered evidence corpus the teacher's
propose step consumes: per-language per-cluster JSON, ranked by the taxonomy's
``frequency × severity × (1 + is_tool_missing_capability × 2)`` rule, with the
fix recommendation (fix_tier, component_kind) drawn from the taxonomy table.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from autocode.anvil.teacher.distill import (
    AttributedTrajectory,
    DistillError,
    attributed_from_packets,
    distill,
    distilled_root,
    read_corpus,
    write_corpus,
)
from autocode.anvil.teacher.schemas import (
    Layer,
    RootCause,
    Step,
    Task,
    Trajectory,
    Verdict,
    VerdictLabel,
)
from autocode.anvil.teacher.taxonomy import (
    FAILURE_TABLE,
    RootCauseClass,
)


def _traj(
    *,
    tid: str,
    label: str = VerdictLabel.FAIL.value,
    l4_fraction: float = 0.25,
    wall_s: float = 2.0,
    instruction: str = "do X",
) -> Trajectory:
    n_steps = 4
    n_l4 = round(n_steps * l4_fraction)
    return Trajectory(
        trajectory_id=tid,
        task=Task(instruction=instruction),
        steps=[
            Step(i=i, layer=Layer.L4.value if i < n_l4 else Layer.L1.value)
            for i in range(n_steps)
        ],
        outcome=Verdict(label=label),
        cost={"usd": 0.0, "wall_s": wall_s},
    )


def _attr(
    *,
    tid: str,
    rc_class: str,
    language: str = "python",
    label: str = VerdictLabel.FAIL.value,
    explanation: str = "e",
    evidence_step: int = 2,
    instruction: str = "do X",
) -> AttributedTrajectory:
    return AttributedTrajectory(
        trajectory=_traj(tid=tid, label=label, instruction=instruction),
        root_cause=RootCause(
            category=rc_class,
            evidence_step=evidence_step,
            explanation=explanation,
        ),
        language=language,
    )


# ---------------------------------------------------------------------------
# distill()
# ---------------------------------------------------------------------------


def test_distill_clusters_by_language_and_root_cause() -> None:
    attributed = [
        _attr(tid="t1", rc_class=RootCauseClass.TOOL_MISSING_CAPABILITY.value),
        _attr(tid="t2", rc_class=RootCauseClass.TOOL_MISSING_CAPABILITY.value),
        _attr(tid="t3", rc_class=RootCauseClass.RETRIEVAL_MISS.value),
        _attr(tid="t4", rc_class=RootCauseClass.TOOL_BAD_ARGS.value, language="rust"),
    ]
    corpus = distill(attributed, generated_at="2026-06-22T00:00:00Z")
    # Three clusters: python/tool.missing_capability, python/retrieval.miss, rust/tool.bad_args
    assert len(corpus.clusters) == 3
    languages = {c.language for c in corpus.clusters}
    assert languages == {"python", "rust"}


def test_distill_ranks_tool_missing_capability_top_via_x3_multiplier() -> None:
    # Two retrieval.miss vs one tool.missing_capability. Same severity (0.8):
    #   retrieval: rank = 2 × 0.8 × 1   = 1.6
    #   missing:   rank = 1 × 0.8 × 3   = 2.4  <- wins despite lower frequency.
    attributed = [
        _attr(tid="r1", rc_class=RootCauseClass.RETRIEVAL_MISS.value),
        _attr(tid="r2", rc_class=RootCauseClass.RETRIEVAL_MISS.value),
        _attr(tid="m1", rc_class=RootCauseClass.TOOL_MISSING_CAPABILITY.value),
    ]
    corpus = distill(attributed, generated_at="now")
    assert corpus.clusters[0].root_cause_class == RootCauseClass.TOOL_MISSING_CAPABILITY.value
    assert corpus.clusters[0].layer2.frequency == 1
    assert corpus.clusters[1].root_cause_class == RootCauseClass.RETRIEVAL_MISS.value
    assert corpus.clusters[1].layer2.frequency == 2


def test_distill_layer3_fix_recommendation_matches_taxonomy() -> None:
    attributed = [_attr(tid="t1", rc_class=RootCauseClass.CONTEXT_OVERFLOW.value)]
    corpus = distill(attributed, generated_at="now")
    cluster = corpus.clusters[0]
    expected = FAILURE_TABLE[RootCauseClass.CONTEXT_OVERFLOW.value]
    assert cluster.layer3.fix_tier == expected.fix_tier
    assert cluster.layer3.component_kind == expected.component_kind
    assert cluster.layer3.manifest_target_hint.startswith(expected.component_kind)


def test_distill_layer0_captures_trajectory_metadata() -> None:
    attributed = [
        _attr(tid="t1", rc_class=RootCauseClass.RETRIEVAL_MISS.value, instruction="add a flag"),
        _attr(tid="t2", rc_class=RootCauseClass.RETRIEVAL_MISS.value, instruction="add another"),
    ]
    corpus = distill(attributed, generated_at="now")
    cluster = corpus.clusters[0]
    assert len(cluster.layer0) == 2
    ids = {entry.task_instruction for entry in cluster.layer0}
    assert ids == {"add a flag", "add another"}


def test_distill_layer2_has_edge_cost_metrics() -> None:
    attributed = [
        _attr(tid="t1", rc_class=RootCauseClass.RETRIEVAL_MISS.value),
        _attr(tid="t2", rc_class=RootCauseClass.RETRIEVAL_MISS.value),
    ]
    corpus = distill(attributed, generated_at="now")
    m = corpus.clusters[0].layer2
    assert m.frequency == 2
    assert m.layer_distribution_L4 == pytest.approx(0.25, abs=1e-6)  # noqa: N815
    assert m.latency_p50 == pytest.approx(2.0, abs=1e-6)
    assert m.tokens_per_task >= 0.0
    assert len(m.sample_trajectory_ids) == 2


def test_distill_severity_averages_across_verdict_labels() -> None:
    # ERROR severity=1.0, PARTIAL severity=0.4 -> mean 0.7.
    rc = RootCauseClass.RETRIEVAL_MISS.value
    attributed = [
        _attr(tid="t1", rc_class=rc, label=VerdictLabel.ERROR.value),
        _attr(tid="t2", rc_class=rc, label=VerdictLabel.PARTIAL.value),
    ]
    corpus = distill(attributed, generated_at="now")
    assert corpus.clusters[0].layer2.severity == pytest.approx(0.7, abs=1e-6)


def test_distill_empty_input_raises() -> None:
    with pytest.raises(DistillError, match="no attributed"):
        distill([], generated_at="now")


def test_distill_top_n_across_languages() -> None:
    attributed = [
        _attr(tid="t1", rc_class=RootCauseClass.TOOL_MISSING_CAPABILITY.value, language="python"),
        _attr(tid="t2", rc_class=RootCauseClass.TOOL_MISSING_CAPABILITY.value, language="rust"),
        _attr(tid="t3", rc_class=RootCauseClass.TOOL_MISSING_CAPABILITY.value, language="go"),
    ]
    corpus = distill(attributed, generated_at="now")
    top2 = corpus.top(2)
    assert len(top2) == 2
    assert all(c.layer2.rank >= top2[-1].layer2.rank for c in top2)


def test_distill_by_language_filters() -> None:
    attributed = [
        _attr(tid="t1", rc_class=RootCauseClass.TOOL_MISSING_CAPABILITY.value, language="python"),
        _attr(tid="t2", rc_class=RootCauseClass.TOOL_MISSING_CAPABILITY.value, language="rust"),
    ]
    corpus = distill(attributed, generated_at="now")
    py = corpus.by_language("python")
    assert len(py) == 1
    assert py[0].language == "python"


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def test_write_corpus_writes_per_lang_per_cluster_files(tmp_path: Path) -> None:
    attributed = [
        _attr(tid="t1", rc_class=RootCauseClass.TOOL_MISSING_CAPABILITY.value),
        _attr(tid="t2", rc_class=RootCauseClass.RETRIEVAL_MISS.value, language="rust"),
    ]
    corpus = distill(attributed, generated_at="now", source="test")
    index = write_corpus(corpus, root=tmp_path)
    assert index.is_file()
    assert index.name == "corpus.json"
    # One file per (lang, root_cause_class).
    py_missing = tmp_path / "teacher" / "distilled" / "python" / "tool_missing_capability.json"
    rust_miss = tmp_path / "teacher" / "distilled" / "rust" / "retrieval_miss.json"
    assert py_missing.is_file()
    assert rust_miss.is_file()


def test_read_corpus_round_trips(tmp_path: Path) -> None:
    attributed = [
        _attr(tid="t1", rc_class=RootCauseClass.TOOL_MISSING_CAPABILITY.value),
        _attr(tid="t2", rc_class=RootCauseClass.RETRIEVAL_MISS.value, language="rust"),
    ]
    corpus = distill(attributed, generated_at="2026-06-22T00:00:00Z", source="test")
    write_corpus(corpus, root=tmp_path)
    reloaded = read_corpus(tmp_path)
    assert reloaded is not None
    assert reloaded.trajectory_count == 2
    assert len(reloaded.clusters) == 2
    assert {c.root_cause_class for c in reloaded.clusters} == {
        RootCauseClass.TOOL_MISSING_CAPABILITY.value,
        RootCauseClass.RETRIEVAL_MISS.value,
    }
    # Top-ranked is the tool.missing_capability one (×3 multiplier).
    assert reloaded.clusters[0].layer2.rank >= reloaded.clusters[1].layer2.rank


def test_read_corpus_returns_none_when_absent(tmp_path: Path) -> None:
    assert read_corpus(tmp_path) is None


def test_distilled_root_uses_anvil_layout(tmp_path: Path) -> None:
    # Resolves under <anvil>/teacher/distilled/.
    root = distilled_root(tmp_path)
    assert root == tmp_path / "teacher" / "distilled"


# ---------------------------------------------------------------------------
# attributed_from_packets()
# ---------------------------------------------------------------------------


def test_attributed_from_packets_accepts_3tuple_form() -> None:
    tj = _traj(tid="t1")
    rc = RootCause(category=RootCauseClass.RETRIEVAL_MISS.value)
    packets = [(tj, rc, "python"), (tj, rc, "rust")]
    attributed = attributed_from_packets(packets)
    assert len(attributed) == 2
    assert attributed[0].language == "python"
    assert attributed[1].language == "rust"


def test_attributed_from_packets_passes_attributed_through() -> None:
    a = _attr(tid="t1", rc_class=RootCauseClass.RETRIEVAL_MISS.value)
    out = attributed_from_packets([a])
    assert out == [a]


# ---------------------------------------------------------------------------
# Smoke: distill output is JSON-serializable for the corpus.json index
# ---------------------------------------------------------------------------


def test_distill_corpus_to_dict_is_json_serializable() -> None:
    attributed = [
        _attr(tid="t1", rc_class=RootCauseClass.TOOL_MISSING_CAPABILITY.value),
        _attr(tid="t2", rc_class=RootCauseClass.RETRIEVAL_MISS.value, language="rust"),
    ]
    corpus = distill(attributed, generated_at="2026-06-22T00:00:00Z", source="test")
    blob = json.dumps(corpus.to_dict(), indent=2)
    assert "layer0_evidence" in blob
    assert "layer3_fix" in blob
    parsed = json.loads(blob)
    assert len(parsed["clusters"]) == 2


# ---------------------------------------------------------------------------
# CLI smoke (sense command)
# ---------------------------------------------------------------------------


def test_cli_sense_command_with_no_packets_exits_zero(tmp_path: Path) -> None:
    from typer.testing import CliRunner

    from autocode.cli import app

    runner = CliRunner()
    # Empty anvil root: no teacher_runs/ dir, no packets.
    result = runner.invoke(
        app, ["anvil", "teacher", "sense", "--anvil-root", str(tmp_path)]
    )
    assert result.exit_code == 0, result.output
    assert "No teaching packets" in result.output


def test_cli_sense_command_clusters_seeded_packets(tmp_path: Path) -> None:
    from typer.testing import CliRunner

    from autocode.anvil.teacher.schemas import (
        Provenance,
        ScoreBreakdown,
        TeachingPacket,
    )
    from autocode.cli import app

    runner = CliRunner()
    runs = tmp_path / "teacher_runs"
    runs.mkdir(parents=True)
    for rc, tid in [
        (RootCauseClass.TOOL_MISSING_CAPABILITY.value, "t-missing"),
        (RootCauseClass.TOOL_MISSING_CAPABILITY.value, "t-missing-2"),
        (RootCauseClass.RETRIEVAL_MISS.value, "t-miss"),
    ]:
        pkt = TeachingPacket(
            packet_id=f"p-{tid}",
            trajectory_id=tid,
            verdict=Verdict(label=VerdictLabel.FAIL.value),
            root_cause=RootCause(category=rc, evidence_step=1, explanation="x"),
            score_breakdown=ScoreBreakdown(),
            harness_fix=None,
            playbook_delta=None,
            provenance=Provenance(),
        )
        (runs / tid).mkdir(parents=True, exist_ok=True)
        (runs / tid / "teaching_packet.json").write_text(pkt.to_json(), encoding="utf-8")

    result = runner.invoke(
        app, ["anvil", "teacher", "sense", "--anvil-root", str(tmp_path)]
    )
    assert result.exit_code == 0, result.output
    assert "tool.missing_capability" in result.output
    assert "retrieval.miss" in result.output
    # Top-ranked cluster is the tool.missing_capability one (×3 multiplier).
    tool_pos = result.output.index("tool.missing_capability")
    miss_pos = result.output.index("retrieval.miss")
    assert tool_pos < miss_pos

