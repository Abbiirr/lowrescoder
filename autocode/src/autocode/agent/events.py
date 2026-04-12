"""Canonical orchestration event schema.

Defines a single event envelope that all orchestration subsystems produce,
enabling unified audit trail, metrics, and external consumption.

Usage:
    from autocode.agent.events import OrchestratorEvent, EventType, SqliteEventSink

    sink = SqliteEventSink(conn)
    event = OrchestratorEvent(event_type=EventType.TASK_CREATED, session_id="s1")
    sink.emit(event)
"""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class EventType(StrEnum):
    """Canonical orchestration event types."""

    # Session lifecycle
    SESSION_STARTED = "session_started"
    SESSION_ENDED = "session_ended"

    # Task lifecycle
    TASK_CREATED = "task_created"
    TASK_CLAIMED = "task_claimed"
    TASK_RELEASED = "task_released"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_ESCALATED = "task_escalated"

    # Agent messaging
    MESSAGE_SENT = "message_sent"
    MESSAGE_DELIVERED = "message_delivered"
    MESSAGE_CLAIMED = "message_claimed"

    # Tool execution
    TOOL_CALLED = "tool_called"
    TOOL_COMPLETED = "tool_completed"
    TOOL_BLOCKED = "tool_blocked"

    # Approval
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_GRANTED = "approval_granted"
    APPROVAL_DENIED = "approval_denied"

    # Subagent lifecycle
    SUBAGENT_SPAWNED = "subagent_spawned"
    SUBAGENT_COMPLETED = "subagent_completed"
    SUBAGENT_FAILED = "subagent_failed"
    SUBAGENT_CANCELLED = "subagent_cancelled"

    # Budget / cost
    BUDGET_WARNING = "budget_warning"
    BUDGET_EXCEEDED = "budget_exceeded"

    # Routing
    TASK_ROUTED = "task_routed"

    # Pipeline
    PIPELINE_STARTED = "pipeline_started"
    PIPELINE_STEP_COMPLETED = "pipeline_step_completed"
    PIPELINE_COMPLETED = "pipeline_completed"
    PIPELINE_GATE_FAILED = "pipeline_gate_failed"


@dataclass(frozen=True)
class OrchestratorEvent:
    """Canonical event envelope for all orchestration subsystems."""

    event_type: EventType
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(UTC),
    )
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    trace_id: str = ""
    span_id: str = ""
    parent_span_id: str = ""
    source_agent: str = ""
    session_id: str = ""
    task_id: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dict."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "source_agent": self.source_agent,
            "session_id": self.session_id,
            "task_id": self.task_id,
            "payload": self.payload,
            "metadata": self.metadata,
        }


class EventSink(Protocol):
    """Protocol for consuming orchestration events."""

    def emit(self, event: OrchestratorEvent) -> None: ...


class SqliteEventSink:
    """Persists OrchestratorEvents to the orchestrator_events table."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def emit(self, event: OrchestratorEvent) -> None:
        """Persist a single event."""
        self._conn.execute(
            "INSERT INTO orchestrator_events "
            "(event_id, event_type, timestamp, trace_id, span_id, "
            " parent_span_id, source_agent, session_id, task_id, "
            " payload, metadata) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                event.event_id,
                event.event_type.value,
                event.timestamp.isoformat(),
                event.trace_id,
                event.span_id,
                event.parent_span_id,
                event.source_agent,
                event.session_id,
                event.task_id,
                json.dumps(event.payload, default=str),
                json.dumps(event.metadata, default=str),
            ),
        )
        self._conn.commit()

    def query(
        self,
        *,
        session_id: str = "",
        event_type: str = "",
        trace_id: str = "",
        task_id: str = "",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Query events with optional filters."""
        conditions: list[str] = []
        params: list[str | int] = []

        if session_id:
            conditions.append("session_id = ?")
            params.append(session_id)
        if event_type:
            conditions.append("event_type = ?")
            params.append(event_type)
        if trace_id:
            conditions.append("trace_id = ?")
            params.append(trace_id)
        if task_id:
            conditions.append("task_id = ?")
            params.append(task_id)

        where = " AND ".join(conditions) if conditions else "1=1"
        params.append(limit)

        cursor = self._conn.execute(
            f"SELECT * FROM orchestrator_events WHERE {where} "  # noqa: S608
            f"ORDER BY id ASC LIMIT ?",
            params,
        )
        return [dict(row) for row in cursor.fetchall()]

    def count(
        self,
        *,
        session_id: str = "",
        event_type: str = "",
    ) -> int:
        """Count events with optional filters."""
        conditions: list[str] = []
        params: list[str] = []

        if session_id:
            conditions.append("session_id = ?")
            params.append(session_id)
        if event_type:
            conditions.append("event_type = ?")
            params.append(event_type)

        where = " AND ".join(conditions) if conditions else "1=1"
        cursor = self._conn.execute(
            f"SELECT COUNT(*) FROM orchestrator_events WHERE {where}",  # noqa: S608
            params,
        )
        return cursor.fetchone()[0]


class NullEventSink:
    """No-op sink for tests and environments without persistence."""

    def emit(self, event: OrchestratorEvent) -> None:
        pass


class CompositeEventSink:
    """Fan-out to multiple sinks. Failures in one sink don't block others."""

    def __init__(self, sinks: list[EventSink]) -> None:
        self._sinks = sinks

    def emit(self, event: OrchestratorEvent) -> None:
        for sink in self._sinks:
            try:
                sink.emit(event)
            except Exception:
                logger.warning(
                    "EventSink %s failed to emit %s",
                    type(sink).__name__,
                    event.event_type,
                    exc_info=True,
                )
