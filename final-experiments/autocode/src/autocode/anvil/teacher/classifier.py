"""Deterministic root-cause classifier (§3 / §4.4).

Given a student :class:`Trajectory` and its :class:`Verdict`, attribute the
failure to one taxonomy class and point at the decisive step. This is a
*deterministic* heuristic pass — it never calls an LLM, so it is reproducible and
cheap, and it gives the reflector a strong prior the (optional) LLM step can
refine. The flywheel's highest-value class, ``tool.missing_capability``, is
detected first because every L→L4 escalation with no lower-layer tool is a
candidate new deterministic tool (§3.1).

Optional contrast: when a stronger *teacher* trajectory is supplied and it
solved the task with a lower layer than the student, that sharpens the
``tool.missing_capability`` / ``retrieval.miss`` signal (PLAN_05 Channel C).
"""

from __future__ import annotations

from autocode.anvil.teacher.schemas import (
    Layer,
    RootCause,
    Trajectory,
    Verdict,
    VerdictLabel,
)
from autocode.anvil.teacher.taxonomy import RootCauseClass

# A trajectory longer than this with no progress is treated as compaction thrash.
_OVERFLOW_STEP_THRESHOLD = 60
_EARLY_STOP_MAX_STEPS = 2

_TEST_TOOL_HINTS = ("pytest", "test", "verify", "check", "run_tests")


def _escalation_step(tj: Trajectory) -> int:
    """Index of the first step that escalated *up to* L4 from a lower layer."""
    for step in tj.steps:
        if step.escalated_from in (Layer.L1.value, Layer.L2.value, Layer.L3.value):
            return step.i
        if step.action == "escalate" and step.layer == Layer.L4.value:
            return step.i
    return -1


def _has_retrieval(tj: Trajectory) -> bool:
    return any(s.layer == Layer.L2.value or s.action == "retrieve" for s in tj.steps)


def _has_self_check(tj: Trajectory) -> bool:
    for s in tj.steps:
        blob = f"{s.tool} {s.action}".lower()
        if any(hint in blob for hint in _TEST_TOOL_HINTS):
            return True
    return False


def _first_l4_step(tj: Trajectory) -> int:
    for step in tj.steps:
        if step.layer == Layer.L4.value:
            return step.i
    return tj.steps[0].i if tj.steps else -1


def _last_generative_step(tj: Trajectory) -> int:
    for step in reversed(tj.steps):
        if step.action in ("generate", "tool_call", "edit"):
            return step.i
    return tj.steps[-1].i if tj.steps else -1


def _teacher_used_lower_layer(student: Trajectory, teacher: Trajectory | None) -> bool:
    """True when the teacher solved it leaning on L1/L2 while the student burned L4."""
    if teacher is None or not teacher.outcome.is_success:
        return False
    student_l4 = student.layer_distribution.get("L4", 0.0)
    teacher_lower = teacher.layer_distribution.get("L1", 0.0) + teacher.layer_distribution.get(
        "L2", 0.0
    )
    return student_l4 >= 0.5 and teacher_lower > 0.0


def classify(
    trajectory: Trajectory,
    verdict: Verdict | None = None,
    *,
    teacher: Trajectory | None = None,
) -> RootCause:
    """Attribute ``trajectory``'s failure to one taxonomy class with evidence.

    Returns ``RootCause`` with ``category == ""`` for a clean success.
    """
    v = verdict or trajectory.outcome

    if v.label == VerdictLabel.SUCCESS.value:
        return RootCause(
            category=RootCauseClass.NONE.value, evidence_step=-1, explanation="no failure"
        )

    esc = _escalation_step(trajectory)
    has_retrieval = _has_retrieval(trajectory)
    has_self_check = _has_self_check(trajectory)
    n_steps = len(trajectory.steps)
    contrast = _teacher_used_lower_layer(trajectory, teacher)

    # 1. diff did not even apply → the produced edit was malformed.
    if v.label == VerdictLabel.ERROR.value:
        return RootCause(
            category=RootCauseClass.TOOL_BAD_ARGS.value,
            evidence_step=_last_generative_step(trajectory),
            explanation=(
                "The candidate diff did not apply cleanly (verdict=error): the edit "
                "tool was given malformed arguments / wrong context."
            ),
        )

    # 2. tool.missing_capability — the flywheel's best fuel (§3.1, §3.3).
    if esc >= 0 and (v.tests.failed > 0 or v.tests.regressed > 0 or contrast):
        extra = (
            " The teacher solved the same task using lower-layer (L1/L2) tools, "
            "confirming a missing deterministic capability."
            if contrast
            else ""
        )
        return RootCause(
            category=RootCauseClass.TOOL_MISSING_CAPABILITY.value,
            evidence_step=esc,
            explanation=(
                f"Escalated to L4 at step {esc} because no L1/L2 tool exposed the needed "
                f"capability; the L4 reasoning produced a failing result.{extra}"
            ),
        )

    # 2b. teacher contrast alone. Real autocode runs rarely emit explicit
    #     escalation markers, but a stronger teacher solving the same task with
    #     lower-layer (L1/L2) tools while the student burned L4 *is* the
    #     missing-capability signal — the highest-value attribution.
    if contrast:
        return RootCause(
            category=RootCauseClass.TOOL_MISSING_CAPABILITY.value,
            evidence_step=_first_l4_step(trajectory),
            explanation=(
                "The student leaned on L4 reasoning and failed, while the teacher solved the "
                "same task using lower-layer (L1/L2) deterministic tools — a missing "
                "deterministic capability the student had to reason around."
            ),
        )

    # 3. context.overflow — pathological length / compaction thrash takes
    #    precedence: a run this long clearly *tried*, so it is not a retrieval miss.
    if n_steps > _OVERFLOW_STEP_THRESHOLD:
        return RootCause(
            category=RootCauseClass.CONTEXT_OVERFLOW.value,
            evidence_step=trajectory.steps[-1].i,
            explanation=(
                f"Trajectory ran {n_steps} steps without converging — likely budget / "
                "compaction thrash."
            ),
        )

    # 4. retrieval.miss — never even tried to find the relevant code.
    if not has_retrieval and v.label == VerdictLabel.FAIL.value:
        return RootCause(
            category=RootCauseClass.RETRIEVAL_MISS.value,
            evidence_step=trajectory.steps[0].i if trajectory.steps else -1,
            explanation=(
                "No L2 retrieval step ran; the agent edited without locating the relevant "
                "file/symbol, so the fix missed."
            ),
        )

    # 5. reasoning.early_stop — quit too soon.
    if n_steps <= _EARLY_STOP_MAX_STEPS and v.label in (
        VerdictLabel.FAIL.value,
        VerdictLabel.PARTIAL.value,
    ):
        return RootCause(
            category=RootCauseClass.REASONING_EARLY_STOP.value,
            evidence_step=trajectory.steps[-1].i if trajectory.steps else -1,
            explanation=(
                f"Only {n_steps} step(s) before stopping with an incomplete task — the loop "
                "gave up early."
            ),
        )

    # 6. verify.no_self_check — declared done without running tests.
    if not has_self_check and v.label == VerdictLabel.FAIL.value:
        return RootCause(
            category=RootCauseClass.VERIFY_NO_SELF_CHECK.value,
            evidence_step=_last_generative_step(trajectory),
            explanation=(
                "No test/verify step was run before the agent declared the task done; the "
                "failure would have been caught by a self-check."
            ),
        )

    # 7. style.weak_output — correct (tests pass) but lint/types dirty.
    if v.label == VerdictLabel.PARTIAL.value:
        return RootCause(
            category=RootCauseClass.STYLE_WEAK_OUTPUT.value,
            evidence_step=_last_generative_step(trajectory),
            explanation=(
                "Tests pass but lint/types are dirty — the output is correct but unidiomatic."
            ),
        )

    # 8. default — the plan itself was wrong.
    return RootCause(
        category=RootCauseClass.REASONING_WRONG_PLAN.value,
        evidence_step=trajectory.steps[0].i if trajectory.steps else -1,
        explanation="The plan was wrong before tools could help; no cheaper cause fits.",
    )


__all__ = ["classify"]
