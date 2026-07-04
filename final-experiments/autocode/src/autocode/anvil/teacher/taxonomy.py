"""The root-cause taxonomy (§3.1 / §4.4) — the bridge from "agent failed" to
"edit *this* manifest component".

This is the shared vocabulary between the distiller, the teacher, and the
self-maintenance loop. Each class maps to the responsible layer and the cheapest
sufficient fix tier/component, so a teaching packet's ``harness_fix`` can target
a concrete manifest entry rather than waving at "the agent".
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class RootCauseClass(StrEnum):
    """The normative §4.4 failure classes (verbatim string values)."""

    REASONING_WRONG_PLAN = "reasoning.wrong_plan"
    REASONING_EARLY_STOP = "reasoning.early_stop"
    RETRIEVAL_MISS = "retrieval.miss"
    RETRIEVAL_STALE_CONTEXT = "retrieval.stale_context"
    TOOL_WRONG_CHOICE = "tool.wrong_choice"
    TOOL_BAD_ARGS = "tool.bad_args"
    TOOL_MISSING_CAPABILITY = "tool.missing_capability"
    CONTEXT_OVERFLOW = "context.overflow"
    VERIFY_NO_SELF_CHECK = "verify.no_self_check"
    STYLE_WEAK_OUTPUT = "style.weak_output"

    # Anvil sentinel for a run with no failure to attribute (not in §4.4).
    NONE = ""


@dataclass(frozen=True)
class FailureInfo:
    """The §3.1 table row for a class: where it lives and how it's typically fixed."""

    layer: str  # "L1" | "L2" | "L4" | "any" | "—"
    symptom: str
    fix_tier: int  # PLAN escalation ladder: 1=tool, 2=middleware, 3=playbook, 4=prompt
    component_kind: str  # the manifest `kind` a harness_fix would target


# The §3.1 taxonomy table, normative.
FAILURE_TABLE: dict[str, FailureInfo] = {
    RootCauseClass.REASONING_WRONG_PLAN.value: FailureInfo(
        "L4", "Plan was wrong before any tool ran", 4, "system_prompt"
    ),
    RootCauseClass.REASONING_EARLY_STOP.value: FailureInfo(
        "L4", "Quit before task complete", 2, "middleware"
    ),
    RootCauseClass.RETRIEVAL_MISS.value: FailureInfo(
        "L2", "Never found the relevant file/symbol", 1, "tool_implementation"
    ),
    RootCauseClass.RETRIEVAL_STALE_CONTEXT.value: FailureInfo(
        "L2", "Used outdated context after edits", 2, "middleware"
    ),
    RootCauseClass.TOOL_WRONG_CHOICE.value: FailureInfo(
        "any", "Picked the wrong tool", 1, "tool_description"
    ),
    RootCauseClass.TOOL_BAD_ARGS.value: FailureInfo(
        "any", "Right tool, wrong arguments", 1, "tool_description"
    ),
    RootCauseClass.TOOL_MISSING_CAPABILITY.value: FailureInfo(
        "L1", "No deterministic tool existed; escalated to L4", 1, "tool_implementation"
    ),
    RootCauseClass.CONTEXT_OVERFLOW.value: FailureInfo(
        "—", "Ran out of budget / compaction thrash", 2, "middleware"
    ),
    RootCauseClass.VERIFY_NO_SELF_CHECK.value: FailureInfo(
        "—", "Didn't run tests before declaring done", 2, "subagent"
    ),
    RootCauseClass.STYLE_WEAK_OUTPUT.value: FailureInfo(
        "L4", "Correct but ugly/unidiomatic", 3, "long_term_memory"
    ),
}


def is_known_class(value: str) -> bool:
    return value in FAILURE_TABLE


def fix_info(cls_value: str) -> FailureInfo | None:
    return FAILURE_TABLE.get(cls_value)


def cluster_rank(*, frequency: int, severity: float, is_tool_missing_capability: bool) -> float:
    """The §3.3 cluster-ranking rule — the flywheel's bias.

    ``rank = frequency × severity × (1 + is_tool_missing_capability × 2)``

    The ×3 multiplier for ``tool.missing_capability`` is deliberate: those
    clusters produce durable tier-1 (new deterministic tool) fixes that move work
    *down* the escalation ladder for a whole class of tasks.
    """
    bonus = 1 + (2 if is_tool_missing_capability else 0)
    return float(frequency) * float(severity) * float(bonus)


def rank_clusters(clusters: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sort failure clusters by :func:`cluster_rank`, descending.

    Each cluster dict must carry ``frequency`` (int), ``severity`` (float) and
    ``class`` (a taxonomy value). The returned list is a new list with a
    ``rank`` key added to each cluster.
    """
    ranked = []
    for c in clusters:
        cls = c.get("class", "")
        r = cluster_rank(
            frequency=int(c.get("frequency", 0)),
            severity=float(c.get("severity", 1.0)),
            is_tool_missing_capability=(cls == RootCauseClass.TOOL_MISSING_CAPABILITY.value),
        )
        ranked.append({**c, "rank": r})
    ranked.sort(key=lambda c: c["rank"], reverse=True)
    return ranked


__all__ = [
    "RootCauseClass",
    "FailureInfo",
    "FAILURE_TABLE",
    "is_known_class",
    "fix_info",
    "cluster_rank",
    "rank_clusters",
]
