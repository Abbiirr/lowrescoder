"""Session memory consolidation — extract and persist learnings between sessions.

Inspired by the autoDream pattern: orient/gather/consolidate/prune.
Runs after session end to distill useful patterns into persistent memory.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class SessionLearning:
    """A single learning extracted from a session."""

    category: str  # "file_pattern", "error_fix", "tool_usage", "project_structure"
    summary: str
    evidence: str  # the raw data that supports this learning
    confidence: float = 0.8  # 0.0-1.0
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass
class ConsolidationResult:
    """Result of a consolidation pass."""

    learnings_gathered: int
    learnings_kept: int
    learnings_pruned: int
    categories: dict[str, int] = field(default_factory=dict)


class SessionConsolidator:
    """Consolidates session history into persistent memory.

    Four-phase pipeline:
    1. Orient: Load session metadata and recent history
    2. Gather: Extract candidate learnings from tool calls, errors, file patterns
    3. Consolidate: Merge with existing memory, deduplicate
    4. Prune: Remove stale or low-confidence entries
    """

    def __init__(self, max_learnings: int = 100) -> None:
        self._max_learnings = max_learnings
        self._existing_learnings: list[SessionLearning] = []

    def orient(self, session_messages: list[dict[str, Any]]) -> dict[str, Any]:
        """Phase 1: Analyze session to understand scope and activity."""
        stats: dict[str, Any] = {
            "total_messages": len(session_messages),
            "user_messages": sum(1 for m in session_messages if m.get("role") == "user"),
            "assistant_messages": sum(1 for m in session_messages if m.get("role") == "assistant"),
            "tool_calls": 0,
            "files_mentioned": set(),
            "errors_seen": [],
        }
        for msg in session_messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                # Count tool-related patterns
                if "Error" in content or "error" in content:
                    stats["errors_seen"].append(content[:200])
            # Count tool_calls in assistant messages
            if msg.get("role") == "assistant" and msg.get("tool_calls"):
                stats["tool_calls"] += len(msg["tool_calls"])
        stats["files_mentioned"] = list(stats["files_mentioned"])
        return stats

    def gather(
        self,
        session_messages: list[dict[str, Any]],
        orientation: dict[str, Any],
    ) -> list[SessionLearning]:
        """Phase 2: Extract candidate learnings from session history."""
        learnings: list[SessionLearning] = []

        # Extract file patterns from tool calls
        files_edited: set[str] = set()
        for msg in session_messages:
            if msg.get("role") == "assistant" and msg.get("tool_calls"):
                for tc in msg["tool_calls"]:
                    fn = tc.get("function", {})
                    name = fn.get("name", "")
                    args = fn.get("arguments", {})
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except (json.JSONDecodeError, TypeError):
                            args = {}
                    if name in ("write_file", "edit_file") and "path" in args:
                        files_edited.add(args["path"])

        if files_edited:
            learnings.append(
                SessionLearning(
                    category="file_pattern",
                    summary=f"Files modified in session: {', '.join(sorted(files_edited)[:10])}",
                    evidence=f"{len(files_edited)} files edited",
                )
            )

        # Extract error patterns
        for error in orientation.get("errors_seen", [])[:5]:
            learnings.append(
                SessionLearning(
                    category="error_fix",
                    summary=f"Error encountered: {error[:100]}",
                    evidence=error[:200],
                    confidence=0.6,
                )
            )

        # Extract tool usage patterns
        tool_counts: dict[str, int] = {}
        for msg in session_messages:
            if msg.get("role") == "assistant" and msg.get("tool_calls"):
                for tc in msg["tool_calls"]:
                    name = tc.get("function", {}).get("name", "unknown")
                    tool_counts[name] = tool_counts.get(name, 0) + 1

        if tool_counts:
            top_tools = sorted(tool_counts.items(), key=lambda x: -x[1])[:5]
            learnings.append(
                SessionLearning(
                    category="tool_usage",
                    summary=f"Most used tools: {', '.join(f'{n}({c})' for n, c in top_tools)}",
                    evidence=json.dumps(tool_counts),
                )
            )

        return learnings

    def consolidate(self, new_learnings: list[SessionLearning]) -> list[SessionLearning]:
        """Phase 3: Merge new learnings with existing, deduplicate."""
        merged = list(self._existing_learnings)

        existing_summaries = {learning.summary for learning in merged}
        for learning in new_learnings:
            if learning.summary not in existing_summaries:
                merged.append(learning)
                existing_summaries.add(learning.summary)

        return merged

    def prune(self, learnings: list[SessionLearning]) -> list[SessionLearning]:
        """Phase 4: Remove low-confidence and excess entries."""
        # Sort by confidence descending
        sorted_learnings = sorted(learnings, key=lambda learning: -learning.confidence)
        # Keep only up to max_learnings
        return sorted_learnings[: self._max_learnings]

    def build_carry_forward_summary(
        self,
        session_messages: list[dict[str, Any]],
        *,
        max_objective_chars: int = 240,
    ) -> str:
        """Build a structured carry-forward summary for future iterations.

        The goal is not to fully summarize the conversation, but to preserve
        the highest-signal state needed to continue work after compaction:
        objective, files touched, tools used, errors, and distilled learnings.
        """
        orientation = self.orient(session_messages)
        learnings = self.gather(session_messages, orientation)

        first_user = next(
            (
                str(msg.get("content", "")).strip()
                for msg in session_messages
                if msg.get("role") == "user" and str(msg.get("content", "")).strip()
            ),
            "",
        )
        latest_user = next(
            (
                str(msg.get("content", "")).strip()
                for msg in reversed(session_messages)
                if msg.get("role") == "user" and str(msg.get("content", "")).strip()
            ),
            "",
        )
        if first_user:
            objective = first_user[:max_objective_chars]
        elif latest_user:
            objective = latest_user[:max_objective_chars]
        else:
            objective = "No explicit objective recorded."

        files_read: list[str] = []
        files_modified: list[str] = []
        tasks_created: list[str] = []
        decisions: list[str] = []
        blockers: list[str] = []
        next_actions: list[str] = []

        def _append_unique(items: list[str], value: str, *, limit: int = 5) -> None:
            cleaned = value.strip()
            if not cleaned or cleaned in items or len(items) >= limit:
                return
            items.append(cleaned)

        for msg in session_messages:
            role = str(msg.get("role", ""))
            content = str(msg.get("content", "")).strip()
            tool_calls = msg.get("tool_calls", [])
            if role == "assistant" and isinstance(tool_calls, list):
                for tc in tool_calls:
                    function = tc.get("function", {}) if isinstance(tc, dict) else {}
                    tool_name = str(function.get("name", ""))
                    arguments = function.get("arguments", {})
                    if isinstance(arguments, str):
                        try:
                            arguments = json.loads(arguments)
                        except json.JSONDecodeError:
                            arguments = {}
                    if not isinstance(arguments, dict):
                        arguments = {}
                    path = str(arguments.get("path", "")).strip()
                    if tool_name == "read_file" and path:
                        _append_unique(files_read, path)
                    elif tool_name in {"write_file", "edit_file"} and path:
                        _append_unique(files_modified, path)
                    elif tool_name == "create_task":
                        title = str(arguments.get("title", "")).strip()
                        if title:
                            _append_unique(tasks_created, title)

            lowered = content.lower()
            if not content:
                continue
            if "error" in lowered or "failed" in lowered or "blocked" in lowered:
                _append_unique(blockers, content[:180], limit=6)
            if role == "assistant" and any(
                marker in lowered for marker in ("decision", "decided", "will ", "should ")
            ):
                _append_unique(decisions, content[:180], limit=4)

        latest_assistant = next(
            (
                str(msg.get("content", "")).strip()
                for msg in reversed(session_messages)
                if msg.get("role") == "assistant" and str(msg.get("content", "")).strip()
            ),
            "",
        )
        if tasks_created:
            next_actions.append("Continue the explicit task plan already started in this session.")
        if files_modified:
            next_actions.append(
                "Re-open the most recently modified files and verify the final "
                "state before continuing."
            )
        if blockers:
            next_actions.append(
                "Resolve the active blocker or failure before declaring completion."
            )
        if latest_assistant and latest_assistant[:180] not in next_actions:
            _append_unique(next_actions, latest_assistant[:180], limit=4)

        file_learning = next(
            (learning for learning in learnings if learning.category == "file_pattern"),
            None,
        )
        tool_learning = next(
            (learning for learning in learnings if learning.category == "tool_usage"),
            None,
        )
        error_lines = [str(error)[:180] for error in orientation.get("errors_seen", [])[:3]]

        lines = [
            "Carry-forward summary:",
            "## Objective",
            objective,
        ]

        if files_read:
            lines.append("## Files Read")
            lines.extend(f"- {path}" for path in files_read)

        if files_modified:
            lines.append("## Files Modified")
            lines.extend(f"- {path}" for path in files_modified)
        elif file_learning is not None:
            lines.extend(["## Files Touched", file_learning.summary])

        if tasks_created:
            lines.append("## Plan Progress")
            lines.extend(f"- Created task: {title}" for title in tasks_created)

        if tool_learning is not None:
            lines.extend(["## Tool Patterns", tool_learning.summary])

        if decisions:
            lines.append("## Decisions")
            lines.extend(f"- {decision}" for decision in decisions)

        if blockers or error_lines:
            lines.append("## Blockers")
            lines.extend(f"- {blocker}" for blocker in blockers[:5])
            for error in error_lines:
                if error not in blockers:
                    lines.append(f"- {error}")

        other_learnings = [
            learning.summary
            for learning in learnings
            if learning.category not in {"file_pattern", "tool_usage"}
        ]
        if other_learnings:
            lines.append("## Distilled Learnings")
            lines.extend(f"- {summary}" for summary in other_learnings[:5])

        if next_actions:
            lines.append("## Next Actions")
            lines.extend(f"- {action}" for action in next_actions[:5])

        return "\n".join(lines)

    def run(
        self,
        session_messages: list[dict[str, Any]],
        existing: list[SessionLearning] | None = None,
    ) -> ConsolidationResult:
        """Run the full consolidation pipeline."""
        self._existing_learnings = existing or []

        orientation = self.orient(session_messages)
        gathered = self.gather(session_messages, orientation)
        consolidated = self.consolidate(gathered)
        pruned = self.prune(consolidated)

        categories: dict[str, int] = {}
        for learning in pruned:
            categories[learning.category] = categories.get(learning.category, 0) + 1

        return ConsolidationResult(
            learnings_gathered=len(gathered),
            learnings_kept=len(pruned),
            learnings_pruned=len(consolidated) - len(pruned),
            categories=categories,
        )


# --- Durable-Memory Rules (PLAN.md Section 0.2) ---
# Formalized per the four-plane context model

# Explicit triggers for durable writes — only these can promote to Plane 2
DURABLE_WRITE_TRIGGERS = frozenset(
    {
        "file_pattern",  # File structure observations
        "error_fix",  # Error → fix pattern
        "tool_usage",  # Repeated tool patterns
        "project_structure",  # Architecture decisions
        "gotcha",  # Project-specific quirks
    }
)

# Explicit exclusions — these MUST NOT be promoted to durable memory
# (they belong to Plane 4: ephemeral)
TRANSIENT_EXCLUSIONS = frozenset(
    {
        "result",  # Raw tool output
        "search_hit",  # Individual search results
        "exploration",  # One-off exploration notes
        "failed_attempt",  # Failed attempts without recovery
        "temp",  # Temporary calculations
        "scratch",  # Scratch data
    }
)


def should_promote_to_durable(learning: SessionLearning) -> bool:
    """Determine if a learning should be promoted to durable memory.

    Per the four-plane model:
    - Plane 1 (Durable Instructions): Policy/rules that persist permanently
    - Plane 2 (Durable Memory): Learned project facts that persist until cleared
    - Plane 3 (Live Session): Current task state
    - Plane 4 (Ephemeral): Per-turn scratch (always discarded)

    This implements Plane 2 write rules.
    """
    # Must pass through gather → consolidate → prune pipeline first
    # Only then can something become durable memory

    # Reject if category is in exclusions
    if learning.category in TRANSIENT_EXCLUSIONS:
        return False

    # Must meet confidence threshold
    if learning.confidence < 0.5:
        return False

    # Must be in allowed triggers
    if learning.category not in DURABLE_WRITE_TRIGGERS:
        return False

    return True


def get_plane_for_learning(learning: SessionLearning) -> str:
    """Map a SessionLearning to its context plane name.

    Returns one of: 'durable_memory', 'live_session', 'ephemeral'
    """
    if should_promote_to_durable(learning):
        return "durable_memory"

    if learning.confidence >= 0.3:
        return "live_session"
    return "ephemeral"
