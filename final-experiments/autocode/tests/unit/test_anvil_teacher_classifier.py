"""Tests for the deterministic root-cause classifier (§3)."""

from __future__ import annotations

from autocode.anvil.teacher.classifier import classify
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


def _tj(steps: list[Step], outcome: Verdict, **kw) -> Trajectory:
    tj = Trajectory(
        trajectory_id="tj_c",
        task=Task(instruction="x"),
        steps=steps,
        outcome=outcome,
        **kw,
    )
    tj.compute_layer_distribution()
    return tj


def test_success_yields_no_root_cause() -> None:
    tj = _tj(
        [Step(i=0, layer=Layer.L2.value, action="retrieve", tool="grep")],
        Verdict(
            diff_applies=True,
            build_passed=True,
            tests=TestResults(passed=3),
            lint_clean=True,
            types_clean=True,
            label=VerdictLabel.SUCCESS.value,
        ),
    )
    rc = classify(tj)
    assert rc.category == RootCauseClass.NONE.value


def test_error_label_is_tool_bad_args() -> None:
    tj = _tj(
        [Step(i=0, layer=Layer.L4.value, action="generate", tool="edit")],
        Verdict(diff_applies=False, label=VerdictLabel.ERROR.value),
    )
    rc = classify(tj)
    assert rc.category == RootCauseClass.TOOL_BAD_ARGS.value
    assert rc.evidence_step == 0


def test_canonical_missing_capability_via_escalation() -> None:
    # The §3.2 worked example: retrieve, then escalate L2->L4, one test fails.
    steps = [
        Step(i=0, layer=Layer.L2.value, action="retrieve", tool="grep"),
        Step(i=1, layer=Layer.L4.value, action="escalate", tool="llm", escalated_from="L2"),
        Step(i=2, layer=Layer.L4.value, action="generate", tool="edit"),
    ]
    tj = _tj(
        steps,
        Verdict(
            diff_applies=True,
            build_passed=True,
            tests=TestResults(passed=11, failed=1),
            label=VerdictLabel.FAIL.value,
        ),
    )
    rc = classify(tj)
    assert rc.category == RootCauseClass.TOOL_MISSING_CAPABILITY.value
    assert rc.evidence_step == 1


def test_teacher_contrast_sharpens_missing_capability_even_without_test_fail() -> None:
    student = _tj(
        [
            Step(i=0, layer=Layer.L4.value, action="escalate", tool="llm", escalated_from="L2"),
            Step(i=1, layer=Layer.L4.value, action="generate", tool="edit"),
        ],
        Verdict(
            diff_applies=True,
            build_passed=True,
            tests=TestResults(passed=5, failed=0),
            lint_clean=False,
            types_clean=True,
            label=VerdictLabel.PARTIAL.value,
        ),
    )
    teacher = _tj(
        [
            Step(i=0, layer=Layer.L1.value, action="tool_call", tool="callgraph"),
            Step(i=1, layer=Layer.L2.value, action="retrieve", tool="repomap"),
        ],
        Verdict(
            diff_applies=True,
            build_passed=True,
            tests=TestResults(passed=6),
            lint_clean=True,
            types_clean=True,
            label=VerdictLabel.SUCCESS.value,
        ),
    )
    rc = classify(student, teacher=teacher)
    assert rc.category == RootCauseClass.TOOL_MISSING_CAPABILITY.value
    assert "teacher solved" in rc.explanation.lower()


def test_contrast_alone_triggers_missing_capability_without_escalation_marker() -> None:
    # Real autocode runs lack explicit escalation markers: student is all-L4 and
    # failed; teacher solved with L1/L2. Contrast alone => missing_capability.
    student = _tj(
        [
            Step(i=0, layer=Layer.L4.value, action="plan", tool=""),
            Step(i=1, layer=Layer.L4.value, action="generate", tool="edit_file"),
        ],
        Verdict(
            diff_applies=True,
            build_passed=True,
            tests=TestResults(passed=0, failed=1),
            label=VerdictLabel.FAIL.value,
        ),
    )
    teacher = _tj(
        [
            Step(i=0, layer=Layer.L1.value, action="tool_call", tool="callgraph"),
            Step(i=1, layer=Layer.L2.value, action="retrieve", tool="repomap"),
        ],
        Verdict(
            diff_applies=True,
            build_passed=True,
            tests=TestResults(passed=5),
            lint_clean=True,
            types_clean=True,
            label=VerdictLabel.SUCCESS.value,
        ),
    )
    rc = classify(student, teacher=teacher)
    assert rc.category == RootCauseClass.TOOL_MISSING_CAPABILITY.value
    assert rc.evidence_step == 0


def test_retrieval_miss_when_no_l2_step() -> None:
    tj = _tj(
        [Step(i=0, layer=Layer.L4.value, action="generate", tool="edit")],
        Verdict(
            diff_applies=True,
            build_passed=True,
            tests=TestResults(passed=0, failed=2),
            label=VerdictLabel.FAIL.value,
        ),
    )
    # one step => could be early stop; make it 3 generative steps so early-stop doesn't fire
    tj = _tj(
        [
            Step(i=0, layer=Layer.L4.value, action="plan", tool=""),
            Step(i=1, layer=Layer.L4.value, action="generate", tool="edit"),
            Step(i=2, layer=Layer.L4.value, action="generate", tool="edit"),
        ],
        Verdict(
            diff_applies=True,
            build_passed=True,
            tests=TestResults(passed=0, failed=2),
            label=VerdictLabel.FAIL.value,
        ),
    )
    rc = classify(tj)
    assert rc.category == RootCauseClass.RETRIEVAL_MISS.value


def test_early_stop_when_too_few_steps() -> None:
    tj = _tj(
        [Step(i=0, layer=Layer.L2.value, action="retrieve", tool="grep")],
        Verdict(
            diff_applies=True,
            build_passed=True,
            tests=TestResults(passed=0, failed=1),
            label=VerdictLabel.FAIL.value,
        ),
    )
    rc = classify(tj)
    assert rc.category == RootCauseClass.REASONING_EARLY_STOP.value


def test_verify_no_self_check() -> None:
    tj = _tj(
        [
            Step(i=0, layer=Layer.L2.value, action="retrieve", tool="grep"),
            Step(i=1, layer=Layer.L4.value, action="generate", tool="edit"),
            Step(i=2, layer=Layer.L4.value, action="generate", tool="edit"),
        ],
        Verdict(
            diff_applies=True,
            build_passed=True,
            tests=TestResults(passed=0, failed=1),
            label=VerdictLabel.FAIL.value,
        ),
    )
    rc = classify(tj)
    assert rc.category == RootCauseClass.VERIFY_NO_SELF_CHECK.value


def test_style_weak_output_on_partial() -> None:
    tj = _tj(
        [
            Step(i=0, layer=Layer.L2.value, action="retrieve", tool="grep"),
            Step(i=1, layer=Layer.L4.value, action="generate", tool="pytest"),
            Step(i=2, layer=Layer.L4.value, action="generate", tool="edit"),
        ],
        Verdict(
            diff_applies=True,
            build_passed=True,
            tests=TestResults(passed=4),
            lint_clean=False,
            types_clean=True,
            label=VerdictLabel.PARTIAL.value,
        ),
    )
    rc = classify(tj)
    assert rc.category == RootCauseClass.STYLE_WEAK_OUTPUT.value


def test_context_overflow_on_huge_trajectory() -> None:
    steps = [Step(i=n, layer=Layer.L4.value, action="generate", tool="pytest") for n in range(80)]
    tj = _tj(
        steps,
        Verdict(
            diff_applies=True,
            build_passed=True,
            tests=TestResults(passed=0, failed=1),
            label=VerdictLabel.FAIL.value,
        ),
    )
    rc = classify(tj)
    assert rc.category == RootCauseClass.CONTEXT_OVERFLOW.value
