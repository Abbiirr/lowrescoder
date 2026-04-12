"""Tests for the canonical orchestration event schema."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone

import pytest

from autocode.agent.events import (
    CompositeEventSink,
    EventType,
    NullEventSink,
    OrchestratorEvent,
    SqliteEventSink,
)
from autocode.session.models import ensure_tables


@pytest.fixture()
def conn():
    """In-memory SQLite with all tables + migrations."""
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    ensure_tables(db)
    return db


@pytest.fixture()
def sink(conn: sqlite3.Connection) -> SqliteEventSink:
    return SqliteEventSink(conn)


# ── OrchestratorEvent ──


class TestOrchestratorEvent:
    def test_creation_with_defaults(self) -> None:
        event = OrchestratorEvent(event_type=EventType.SESSION_STARTED)
        assert event.event_type == EventType.SESSION_STARTED
        assert event.event_id  # non-empty
        assert event.timestamp.tzinfo is not None
        assert event.trace_id == ""
        assert event.payload == {}

    def test_to_dict_roundtrip(self) -> None:
        event = OrchestratorEvent(
            event_type=EventType.TASK_CREATED,
            trace_id="trace-1",
            span_id="span-1",
            source_agent="orchestrator",
            session_id="sess-1",
            task_id="task-1",
            payload={"title": "Fix bug"},
            metadata={"priority": 1},
        )
        d = event.to_dict()
        assert d["event_type"] == "task_created"
        assert d["trace_id"] == "trace-1"
        assert d["payload"]["title"] == "Fix bug"
        assert d["metadata"]["priority"] == 1
        # Timestamp is ISO format
        datetime.fromisoformat(d["timestamp"])

    def test_event_id_uniqueness(self) -> None:
        e1 = OrchestratorEvent(event_type=EventType.SESSION_STARTED)
        e2 = OrchestratorEvent(event_type=EventType.SESSION_STARTED)
        assert e1.event_id != e2.event_id

    def test_frozen_immutability(self) -> None:
        event = OrchestratorEvent(event_type=EventType.SESSION_STARTED)
        with pytest.raises(AttributeError):
            event.event_type = EventType.SESSION_ENDED  # type: ignore[misc]


# ── EventType ──


class TestEventType:
    def test_all_types_are_strings(self) -> None:
        for et in EventType:
            assert isinstance(et.value, str)

    def test_values_are_snake_case(self) -> None:
        for et in EventType:
            assert et.value == et.value.lower()
            assert " " not in et.value

    def test_covers_key_lifecycle_events(self) -> None:
        expected = {
            "session_started", "session_ended",
            "task_created", "task_completed",
            "message_sent", "tool_called",
            "subagent_spawned", "subagent_completed",
            "approval_requested",
        }
        actual = {et.value for et in EventType}
        assert expected.issubset(actual)


# ── SqliteEventSink ──


class TestSqliteEventSink:
    def test_emit_persists_event(self, sink: SqliteEventSink, conn: sqlite3.Connection) -> None:
        event = OrchestratorEvent(
            event_type=EventType.SESSION_STARTED,
            session_id="s1",
        )
        sink.emit(event)
        cursor = conn.execute(
            "SELECT * FROM orchestrator_events WHERE event_id = ?",
            (event.event_id,),
        )
        row = cursor.fetchone()
        assert row is not None
        assert row["event_type"] == "session_started"
        assert row["session_id"] == "s1"

    def test_emit_multiple_events(self, sink: SqliteEventSink) -> None:
        for i in range(5):
            sink.emit(OrchestratorEvent(
                event_type=EventType.TOOL_CALLED,
                session_id="s1",
                payload={"index": i},
            ))
        assert sink.count(session_id="s1") == 5

    def test_query_by_session_id(self, sink: SqliteEventSink) -> None:
        sink.emit(OrchestratorEvent(event_type=EventType.TASK_CREATED, session_id="s1"))
        sink.emit(OrchestratorEvent(event_type=EventType.TASK_CREATED, session_id="s2"))
        results = sink.query(session_id="s1")
        assert len(results) == 1
        assert results[0]["session_id"] == "s1"

    def test_query_by_event_type(self, sink: SqliteEventSink) -> None:
        sink.emit(OrchestratorEvent(event_type=EventType.TASK_CREATED, session_id="s1"))
        sink.emit(OrchestratorEvent(event_type=EventType.TASK_COMPLETED, session_id="s1"))
        results = sink.query(event_type="task_created")
        assert len(results) == 1

    def test_query_by_trace_id(self, sink: SqliteEventSink) -> None:
        sink.emit(OrchestratorEvent(event_type=EventType.TASK_CREATED, trace_id="t1"))
        sink.emit(OrchestratorEvent(event_type=EventType.TASK_CREATED, trace_id="t2"))
        results = sink.query(trace_id="t1")
        assert len(results) == 1

    def test_query_by_task_id(self, sink: SqliteEventSink) -> None:
        sink.emit(OrchestratorEvent(event_type=EventType.TOOL_CALLED, task_id="task-1"))
        sink.emit(OrchestratorEvent(event_type=EventType.TOOL_CALLED, task_id="task-2"))
        results = sink.query(task_id="task-1")
        assert len(results) == 1

    def test_query_with_limit(self, sink: SqliteEventSink) -> None:
        for _ in range(10):
            sink.emit(OrchestratorEvent(event_type=EventType.TOOL_CALLED, session_id="s1"))
        results = sink.query(session_id="s1", limit=3)
        assert len(results) == 3

    def test_count_all(self, sink: SqliteEventSink) -> None:
        for _ in range(4):
            sink.emit(OrchestratorEvent(event_type=EventType.SESSION_STARTED))
        assert sink.count() == 4

    def test_count_filtered(self, sink: SqliteEventSink) -> None:
        sink.emit(OrchestratorEvent(event_type=EventType.TASK_CREATED, session_id="s1"))
        sink.emit(OrchestratorEvent(event_type=EventType.TASK_CREATED, session_id="s1"))
        sink.emit(OrchestratorEvent(event_type=EventType.TASK_COMPLETED, session_id="s1"))
        assert sink.count(session_id="s1", event_type="task_created") == 2

    def test_payload_stored_as_json(self, sink: SqliteEventSink, conn: sqlite3.Connection) -> None:
        sink.emit(OrchestratorEvent(
            event_type=EventType.TOOL_CALLED,
            payload={"tool": "read_file", "args": {"path": "/tmp/test"}},
        ))
        cursor = conn.execute("SELECT payload FROM orchestrator_events")
        row = cursor.fetchone()
        data = json.loads(row["payload"])
        assert data["tool"] == "read_file"


# ── NullEventSink ──


class TestNullEventSink:
    def test_emit_does_not_raise(self) -> None:
        sink = NullEventSink()
        sink.emit(OrchestratorEvent(event_type=EventType.SESSION_STARTED))


# ── CompositeEventSink ──


class TestCompositeEventSink:
    def test_fanout_to_multiple_sinks(self, conn: sqlite3.Connection) -> None:
        s1 = SqliteEventSink(conn)
        collected: list[OrchestratorEvent] = []

        class ListSink:
            def emit(self, event: OrchestratorEvent) -> None:
                collected.append(event)

        composite = CompositeEventSink([s1, ListSink()])
        event = OrchestratorEvent(event_type=EventType.SESSION_STARTED, session_id="s1")
        composite.emit(event)

        assert s1.count(session_id="s1") == 1
        assert len(collected) == 1

    def test_empty_sinks_list(self) -> None:
        composite = CompositeEventSink([])
        composite.emit(OrchestratorEvent(event_type=EventType.SESSION_STARTED))

    def test_one_failing_sink_does_not_block_others(self) -> None:
        collected: list[OrchestratorEvent] = []

        class FailingSink:
            def emit(self, event: OrchestratorEvent) -> None:
                raise RuntimeError("sink failed")

        class ListSink:
            def emit(self, event: OrchestratorEvent) -> None:
                collected.append(event)

        composite = CompositeEventSink([FailingSink(), ListSink()])
        composite.emit(OrchestratorEvent(event_type=EventType.SESSION_STARTED))
        assert len(collected) == 1
