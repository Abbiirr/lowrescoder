"""Tests for the teacher-mode data contracts (JSON round-trip + key fidelity)."""

from __future__ import annotations

from autocode.anvil.teacher.schemas import (
    HarnessFix,
    Layer,
    ModelInfo,
    Provenance,
    RootCause,
    ScoreBreakdown,
    Step,
    Task,
    TaskSource,
    TeachingPacket,
    TestResults,
    Trajectory,
    Verdict,
    VerdictLabel,
)


def _sample_trajectory() -> Trajectory:
    return Trajectory(
        trajectory_id="tj_test_1",
        task=Task(
            instruction="add a clamp function",
            repo="/tmp/repo",
            commit="abc123",
            source=TaskSource.SYNTHETIC.value,
        ),
        harness_version="manifest@deadbeef",
        model=ModelInfo(alias="coding", provider="openai", is_local=True),
        steps=[
            Step(i=0, layer=Layer.L2.value, action="retrieve", tool="grep"),
            Step(
                i=1,
                layer=Layer.L4.value,
                action="escalate",
                tool="llm",
                escalated_from="L2",
            ),
        ],
        final_diff="--- a\n+++ b\n",
        outcome=Verdict(
            diff_applies=True,
            build_passed=True,
            tests=TestResults(passed=11, failed=1, regressed=0),
            lint_clean=True,
            types_clean=True,
            label=VerdictLabel.FAIL.value,
        ),
        role="student",
    )


def test_trajectory_round_trip() -> None:
    tj = _sample_trajectory()
    again = Trajectory.from_json(tj.to_json())
    assert again.to_dict() == tj.to_dict()
    assert again.task.instruction == "add a clamp function"
    assert again.steps[1].escalated_from == "L2"
    assert again.outcome.tests.failed == 1


def test_compute_layer_distribution() -> None:
    tj = _sample_trajectory()
    dist = tj.compute_layer_distribution()
    assert dist["L2"] == 0.5
    assert dist["L4"] == 0.5
    assert dist["L1"] == 0.0
    assert abs(sum(dist.values()) - 1.0) < 1e-9


def test_root_cause_serialises_class_key() -> None:
    rc = RootCause(category="tool.missing_capability", evidence_step=7, explanation="x")
    d = rc.to_dict()
    # The JSON key must be the literal "class", not "category".
    assert d["class"] == "tool.missing_capability"
    assert "category" not in d
    assert RootCause.from_dict(d).category == "tool.missing_capability"


def test_teaching_packet_round_trip() -> None:
    packet = TeachingPacket(
        packet_id="tp_1",
        trajectory_id="tj_test_1",
        verdict=Verdict(diff_applies=True, build_passed=True, label=VerdictLabel.PARTIAL.value),
        root_cause=RootCause(
            category="retrieval.miss", evidence_step=3, explanation="never found it"
        ),
        score_breakdown=ScoreBreakdown(
            diff_applies=1, build=1, tests=1, lint=0, types=1, style_judge=0.7
        ),
        revision=None,
        harness_fix=HarnessFix(
            target="tool.callgraph.impl",
            kind="tool_implementation",
            sketch="add tree-sitter callgraph",
        ),
        playbook_delta="prefer L2 retrieval before L4 reasoning for callers-of",
        provenance=Provenance(teacher_model="coding", anvil_version="0.1.0", created="2026-06-21"),
    )
    again = TeachingPacket.from_json(packet.to_json())
    assert again.to_dict() == packet.to_dict()
    assert again.harness_fix is not None
    assert again.harness_fix.target == "tool.callgraph.impl"
    assert again.root_cause.to_dict()["class"] == "retrieval.miss"


def test_teaching_packet_optional_harness_fix_none() -> None:
    packet = TeachingPacket(
        packet_id="tp_2",
        trajectory_id="tj_x",
        verdict=Verdict(),
        root_cause=RootCause(category="style.weak_output"),
    )
    again = TeachingPacket.from_dict(packet.to_dict())
    assert again.harness_fix is None
    assert again.playbook_delta is None
