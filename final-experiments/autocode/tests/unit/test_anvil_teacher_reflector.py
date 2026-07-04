"""Tests for the Reflector / teaching-packet generator (§1.2/§3)."""

from __future__ import annotations

import json

from autocode.anvil.teacher.reflector import _extract_json, reflect
from autocode.anvil.teacher.schemas import (
    Layer,
    Step,
    Task,
    TestResults,
    Trajectory,
    Verdict,
    VerdictLabel,
)
from autocode.anvil.teacher.taxonomy import RootCauseClass


def _missing_capability_trajectory() -> Trajectory:
    tj = Trajectory(
        trajectory_id="tj_mc",
        task=Task(instruction="add caller for TokenStore.refresh"),
        steps=[
            Step(i=0, layer=Layer.L2.value, action="retrieve", tool="grep"),
            Step(
                i=1, layer=Layer.L4.value, action="escalate", tool="callgraph", escalated_from="L2"
            ),
            Step(i=2, layer=Layer.L4.value, action="generate", tool="edit"),
        ],
        outcome=Verdict(
            diff_applies=True,
            build_passed=True,
            tests=TestResults(passed=11, failed=1),
            label=VerdictLabel.FAIL.value,
        ),
    )
    tj.compute_layer_distribution()
    return tj


def test_deterministic_packet_for_missing_capability() -> None:
    tj = _missing_capability_trajectory()
    r = reflect(tj, teacher_model="coding", created="2026-06-21")
    pkt = r.packet
    assert pkt.root_cause.category == RootCauseClass.TOOL_MISSING_CAPABILITY.value
    assert pkt.root_cause.evidence_step == 1
    # Executable-first score breakdown: tests failed => tests subscore 0.
    assert pkt.score_breakdown.tests == 0.0
    assert pkt.score_breakdown.diff_applies == 1.0
    # tier-1 class => a harness fix is proposed, targeting a tool implementation.
    assert pkt.harness_fix is not None
    assert pkt.harness_fix.kind == "tool_implementation"
    assert pkt.harness_fix.target.startswith("tool.")
    assert pkt.provenance.anvil_version  # provenance stamped
    # a playbook delta is produced for the failure
    assert r.delta is not None
    assert r.delta.root_cause_class == RootCauseClass.TOOL_MISSING_CAPABILITY.value
    assert r.delta.rule


def test_no_delta_on_success() -> None:
    tj = Trajectory(
        trajectory_id="tj_ok",
        task=Task(instruction="x"),
        steps=[Step(i=0, layer=Layer.L2.value, action="retrieve", tool="grep")],
        outcome=Verdict(
            diff_applies=True,
            build_passed=True,
            tests=TestResults(passed=3),
            lint_clean=True,
            types_clean=True,
            label=VerdictLabel.SUCCESS.value,
        ),
    )
    r = reflect(tj)
    assert r.delta is None
    assert r.packet.root_cause.category == RootCauseClass.NONE.value


def test_style_class_has_no_harness_fix_but_has_delta() -> None:
    tj = Trajectory(
        trajectory_id="tj_style",
        task=Task(instruction="x"),
        steps=[
            Step(i=0, layer=Layer.L2.value, action="retrieve", tool="grep"),
            Step(i=1, layer=Layer.L4.value, action="generate", tool="pytest"),
            Step(i=2, layer=Layer.L4.value, action="generate", tool="edit"),
        ],
        outcome=Verdict(
            diff_applies=True,
            build_passed=True,
            tests=TestResults(passed=4),
            lint_clean=False,
            types_clean=True,
            label=VerdictLabel.PARTIAL.value,
        ),
    )
    r = reflect(tj)
    assert r.packet.root_cause.category == RootCauseClass.STYLE_WEAK_OUTPUT.value
    assert r.packet.harness_fix is None  # tier 3 (playbook), not a structural fix
    assert r.delta is not None  # still worth a playbook lesson


def test_llm_enrichment_overrides_prose_but_not_gate() -> None:
    tj = _missing_capability_trajectory()

    def fake_llm(prompt: str) -> str:
        assert "GROUND TRUTH" in prompt  # verdict is presented as authoritative
        return json.dumps(
            {
                "explanation": "LLM-written explanation",
                "trigger": "needs a call graph across files",
                "rule": "prefer the call-graph tool; escalate only after a 2nd anchor",
                "harness_fix_sketch": "add tree-sitter call graph",
                "revision": None,
                "style_judge": 0.8,
            }
        )

    r = reflect(tj, llm=fake_llm, teacher_model="coding")
    assert r.packet.root_cause.explanation == "LLM-written explanation"
    assert r.delta is not None
    assert r.delta.rule == "prefer the call-graph tool; escalate only after a 2nd anchor"
    assert r.delta.trigger == "needs a call graph across files"
    # style_judge carried as a SECONDARY signal only; tests still gate hard.
    assert r.packet.score_breakdown.style_judge == 0.8
    assert r.packet.score_breakdown.tests == 0.0


def test_llm_garbage_falls_back_to_templates() -> None:
    tj = _missing_capability_trajectory()
    r = reflect(tj, llm=lambda _p: "not json at all")
    assert r.delta is not None
    assert r.delta.rule  # template rule used


def test_teacher_contrast_passed_through() -> None:
    student = _missing_capability_trajectory()
    teacher = Trajectory(
        trajectory_id="tj_teacher",
        task=Task(instruction="x"),
        steps=[Step(i=0, layer=Layer.L1.value, action="tool_call", tool="callgraph")],
        outcome=Verdict(
            diff_applies=True,
            build_passed=True,
            tests=TestResults(passed=12),
            lint_clean=True,
            types_clean=True,
            label=VerdictLabel.SUCCESS.value,
        ),
    )
    teacher.compute_layer_distribution()
    r = reflect(student, teacher=teacher)
    assert r.packet.root_cause.category == RootCauseClass.TOOL_MISSING_CAPABILITY.value


def test_extract_json_handles_prose_wrapping() -> None:
    raw = 'Sure! Here is the result:\n```json\n{"rule": "x", "trigger": "y"}\n```\nDone.'
    data = _extract_json(raw)
    assert data == {"rule": "x", "trigger": "y"}
