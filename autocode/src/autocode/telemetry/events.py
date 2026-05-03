"""Typed telemetry event catalog.

Telemetry is local-only. Event payloads intentionally keep a small common
envelope and leave event-specific fields inside ``data``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

TELEMETRY_EVENT_KINDS: frozenset[str] = frozenset(
    {
        "session_start",
        "session_end",
        "session_resumed",
        "thread_start",
        "thread_fork",
        "thread_archive",
        "turn_start",
        "turn_completed",
        "turn_interrupted",
        "turn_steered",
        "tool_call_started",
        "tool_call_completed",
        "tool_call_failed",
        "tool_output_offloaded",
        "tool_drift_detected",
        "llm_call_completed",
        "cache_breakpoint_applied",
        "compaction_event",
        "cost_limit_warning",
        "approval_requested",
        "approval_granted",
        "approval_denied",
        "permission_escalation",
        "ralph_recovery_fired",
        "entropy_audit_completed",
        "pev_step_failed",
        "slash_command_invoked",
        "feature_flag_toggled",
    }
)


@dataclass(frozen=True)
class TelemetryEvent:
    ts: str
    session_id: str | None
    thread_id: str | None
    turn_id: str | None
    kind: str
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ts": self.ts,
            "session_id": self.session_id,
            "thread_id": self.thread_id,
            "turn_id": self.turn_id,
            "kind": self.kind,
            "data": self.data,
        }
