"""The Reflector — turn a trajectory + verdict into a teaching packet (§1.2/§3).

In ACE terms the runtime is the *Generator* (it produced the trajectory) and this
module is the *Reflector*: it derives concrete, execution-grounded insight from a
(weaker/failed) run, optionally sharpened by contrast with a stronger *teacher*
run. It emits a :class:`TeachingPacket` (root cause + executable score breakdown +
optional harness fix + playbook delta) and the typed :class:`PlaybookDelta` the
Curator appends.

The Reflector is useful with **no LLM** — it runs the deterministic classifier and
per-class rule/sketch templates. When a gateway-backed ``llm`` callable is
injected it asks for a structured JSON refinement (explanation, trigger, rule,
harness-fix sketch, optional revision, style judge) and overrides only the fields
the model returns validly. The LLM never gates anything (§2) — it only enriches
prose and may set the secondary ``style_judge``.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from autocode.anvil import ANVIL_VERSION
from autocode.anvil.teacher.classifier import classify
from autocode.anvil.teacher.schemas import (
    HarnessFix,
    PlaybookDelta,
    Provenance,
    RootCause,
    ScoreBreakdown,
    TeachingPacket,
    Trajectory,
    Verdict,
    VerdictLabel,
)
from autocode.anvil.teacher.signal import is_failure, score_breakdown
from autocode.anvil.teacher.taxonomy import RootCauseClass, fix_info

# llm(prompt) -> raw model text (expected to contain a JSON object)
LLM = Callable[[str], str]


RULE_TEMPLATES: dict[str, str] = {
    RootCauseClass.TOOL_MISSING_CAPABILITY.value: (
        "When the task needs a relationship (callers-of / callees-of / type-of) that no "
        "L1/L2 tool exposes, prefer adding or using a deterministic tool over escalating "
        "to L4 reasoning; only escalate after a second retrieval pass with a different anchor."
    ),
    RootCauseClass.RETRIEVAL_MISS.value: (
        "Before editing, run an L2 retrieval pass to locate the relevant file/symbol; "
        "never edit blind."
    ),
    RootCauseClass.RETRIEVAL_STALE_CONTEXT.value: (
        "Re-read files after edits; never reuse pre-edit context for a dependent change."
    ),
    RootCauseClass.TOOL_WRONG_CHOICE.value: (
        "Match the tool to the task shape; prefer the most specific deterministic tool."
    ),
    RootCauseClass.TOOL_BAD_ARGS.value: (
        "Validate edit arguments against the current file contents before applying; a "
        "non-applying diff means the context was stale."
    ),
    RootCauseClass.REASONING_EARLY_STOP.value: (
        "Do not declare the task done until its acceptance check passes; keep iterating."
    ),
    RootCauseClass.VERIFY_NO_SELF_CHECK.value: (
        "Always run the test/verify step before declaring the task complete."
    ),
    RootCauseClass.CONTEXT_OVERFLOW.value: (
        "Compact and checkpoint aggressively; if the loop exceeds its step budget, "
        "summarize progress and re-plan rather than thrashing."
    ),
    RootCauseClass.STYLE_WEAK_OUTPUT.value: (
        "Match the surrounding code's idioms, naming and formatting; run lint before finishing."
    ),
    RootCauseClass.REASONING_WRONG_PLAN.value: (
        "Re-derive the plan from the acceptance criteria and verify it against the task "
        "before acting."
    ),
}

TRIGGER_TEMPLATES: dict[str, str] = {
    RootCauseClass.TOOL_MISSING_CAPABILITY.value: "task needs a capability no L1/L2 tool exposes",
    RootCauseClass.RETRIEVAL_MISS.value: "task requires locating an unknown file/symbol",
    RootCauseClass.RETRIEVAL_STALE_CONTEXT.value: "a dependent edit follows an earlier edit",
    RootCauseClass.TOOL_WRONG_CHOICE.value: "several tools could apply to the same subtask",
    RootCauseClass.TOOL_BAD_ARGS.value: "an edit/diff is about to be applied",
    RootCauseClass.REASONING_EARLY_STOP.value: "the agent is about to declare done",
    RootCauseClass.VERIFY_NO_SELF_CHECK.value: "the agent is about to declare done without tests",
    RootCauseClass.CONTEXT_OVERFLOW.value: "the loop is approaching its step/token budget",
    RootCauseClass.STYLE_WEAK_OUTPUT.value: "the change is functionally correct but unreviewed",
    RootCauseClass.REASONING_WRONG_PLAN.value: "a task is received before planning",
}

SKETCH_TEMPLATES: dict[str, str] = {
    RootCauseClass.TOOL_MISSING_CAPABILITY.value: (
        "Add an L1/L2 deterministic tool exposing the missing relationship so this never "
        "needs L4 escalation."
    ),
    RootCauseClass.RETRIEVAL_MISS.value: (
        "Strengthen the L2 retriever (repo-map / hybrid search) so the relevant symbol "
        "surfaces without L4."
    ),
    RootCauseClass.RETRIEVAL_STALE_CONTEXT.value: (
        "Add compaction-provenance middleware that invalidates pre-edit context after writes."
    ),
    RootCauseClass.TOOL_WRONG_CHOICE.value: (
        "Sharpen the tool's description so selection is unambiguous."
    ),
    RootCauseClass.TOOL_BAD_ARGS.value: (
        "Tighten the edit tool's arg schema / pre-apply validation."
    ),
    RootCauseClass.REASONING_EARLY_STOP.value: (
        "Add a Ralph-style continuation middleware that resumes until the acceptance check passes."
    ),
    RootCauseClass.VERIFY_NO_SELF_CHECK.value: (
        "Add a reviewer subagent / hook that runs the verifier before completion."
    ),
    RootCauseClass.CONTEXT_OVERFLOW.value: "Improve compaction middleware to bound context growth.",
}


@dataclass
class Reflection:
    packet: TeachingPacket
    delta: PlaybookDelta | None


def _slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return s[:32] or "candidate"


def _proposed_target(root_cause: RootCause, trajectory: Trajectory) -> str:
    info = fix_info(root_cause.category)
    kind = info.component_kind if info else "component"
    # Use the evidence step's tool as a naming hint when available.
    hint = ""
    for s in trajectory.steps:
        if s.i == root_cause.evidence_step and s.tool:
            hint = s.tool
            break
    if root_cause.category == RootCauseClass.TOOL_MISSING_CAPABILITY.value:
        return f"tool.{_slug(hint or trajectory.task.instruction)}.impl"
    return f"{kind}:{root_cause.category}"


def _maybe_harness_fix(root_cause: RootCause, trajectory: Trajectory) -> HarnessFix | None:
    info = fix_info(root_cause.category)
    if info is None or info.fix_tier > 2:  # tier 3 (playbook) / 4 (prompt): no structural fix
        return None
    sketch = SKETCH_TEMPLATES.get(root_cause.category, "Propose a scoped harness change.")
    return HarnessFix(
        target=_proposed_target(root_cause, trajectory),
        kind=info.component_kind,
        sketch=sketch,
    )


def _extract_json(text: str) -> dict[str, Any]:
    """Best-effort: pull the first balanced JSON object out of model output."""
    if not text:
        return {}
    start = text.find("{")
    if start < 0:
        return {}
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                try:
                    parsed: dict[str, Any] = json.loads(text[start : i + 1])
                    return parsed
                except json.JSONDecodeError:
                    return {}
    return {}


def build_reflection_prompt(
    trajectory: Trajectory, verdict: Verdict, root_cause: RootCause, *, teacher: Trajectory | None
) -> str:
    contrast = ""
    if teacher is not None:
        contrast = (
            f"\nA stronger TEACHER solved the same task (label={teacher.outcome.label}, "
            f"layer_distribution={teacher.layer_distribution}). The student's was "
            f"{trajectory.layer_distribution}. Use the contrast to explain what cheaper "
            f"layer the student should have used."
        )
    return (
        "You are the Reflector in an ACE self-improvement loop for a coding agent. "
        "The verdict below is the GROUND TRUTH (executable oracle) — never contradict it.\n\n"
        f"TASK: {trajectory.task.instruction}\n"
        f"VERDICT: {json.dumps(verdict.to_dict())}\n"
        f"ROOT CAUSE (deterministic prior): {root_cause.category} — {root_cause.explanation}\n"
        f"STUDENT STEPS: {len(trajectory.steps)}{contrast}\n\n"
        "Return ONLY a JSON object with keys: explanation (string, why it failed), "
        "trigger (string, the condition that should activate the lesson), rule (string, "
        "the heuristic the agent should follow next time), harness_fix_sketch (string, a "
        "concrete structural fix or empty), revision (string or null, a corrected diff if "
        "you can produce one), style_judge (number 0..1, only meaningful where no test "
        "decided it). Keep rule and trigger reusable across tasks, not specific to this one."
    )


def reflect(
    trajectory: Trajectory,
    verdict: Verdict | None = None,
    *,
    teacher: Trajectory | None = None,
    llm: LLM | None = None,
    teacher_model: str = "",
    language: str = "python",
    created: str = "",
    packet_id: str | None = None,
) -> Reflection:
    """Produce a :class:`TeachingPacket` (+ optional :class:`PlaybookDelta`)."""
    v = verdict or trajectory.outcome
    root_cause = classify(trajectory, v, teacher=teacher)

    # Deterministic baseline.
    rule = RULE_TEMPLATES.get(root_cause.category, "")
    trigger = TRIGGER_TEMPLATES.get(root_cause.category, root_cause.explanation)
    explanation = root_cause.explanation
    revision: str | None = None
    style_judge = 0.0

    # Optional LLM enrichment — overrides only valid, present fields.
    if llm is not None:
        prompt = build_reflection_prompt(trajectory, v, root_cause, teacher=teacher)
        try:
            data = _extract_json(llm(prompt))
        except Exception:  # noqa: BLE001 - the teacher must never crash the loop
            data = {}
        if isinstance(data.get("explanation"), str) and data["explanation"].strip():
            explanation = data["explanation"].strip()
            root_cause = RootCause(
                category=root_cause.category,
                evidence_step=root_cause.evidence_step,
                explanation=explanation,
            )
        if isinstance(data.get("rule"), str) and data["rule"].strip():
            rule = data["rule"].strip()
        if isinstance(data.get("trigger"), str) and data["trigger"].strip():
            trigger = data["trigger"].strip()
        if isinstance(data.get("revision"), str) and data["revision"].strip():
            revision = data["revision"].strip()
        sj = data.get("style_judge")
        if isinstance(sj, (int, float)):
            style_judge = max(0.0, min(1.0, float(sj)))

    harness_fix = _maybe_harness_fix(root_cause, trajectory)
    breakdown: ScoreBreakdown = score_breakdown(v, style_judge=style_judge)
    provenance = Provenance(
        teacher_model=teacher_model, anvil_version=ANVIL_VERSION, created=created
    )

    pid = packet_id or f"tp_{trajectory.trajectory_id}"
    packet = TeachingPacket(
        packet_id=pid,
        trajectory_id=trajectory.trajectory_id,
        verdict=v,
        root_cause=root_cause,
        score_breakdown=breakdown,
        revision=revision,
        harness_fix=harness_fix,
        playbook_delta=rule if rule else None,
        provenance=provenance,
    )

    delta: PlaybookDelta | None = None
    if is_failure(v) and rule and root_cause.category != RootCauseClass.NONE.value:
        delta = PlaybookDelta(
            delta_id=f"pd_{trajectory.trajectory_id}_{_slug(root_cause.category)}",
            trajectory_id=trajectory.trajectory_id,
            verdict=v.label if v.label != VerdictLabel.ERROR.value else "fail",
            root_cause_class=root_cause.category,
            trigger=trigger,
            observation=explanation,
            rule=rule,
            evidence_trajectory=trajectory.trajectory_id,
            language=language,
            created=created,
            provenance=provenance,
        )

    return Reflection(packet=packet, delta=delta)


__all__ = ["LLM", "Reflection", "reflect", "build_reflection_prompt"]
