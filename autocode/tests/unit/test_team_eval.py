"""Tests for TeamEvalDashboard — offline metrics from canonical events."""

from __future__ import annotations

import sqlite3

import pytest

from autocode.agent.events import EventType, OrchestratorEvent, SqliteEventSink
from autocode.eval.team_eval import TeamEvalDashboard, TeamEvalMetrics
from autocode.session.models import ensure_tables


@pytest.fixture()
def conn():
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    ensure_tables(db)
    return db


@pytest.fixture()
def sink(conn: sqlite3.Connection) -> SqliteEventSink:
    return SqliteEventSink(conn)


@pytest.fixture()
def dashboard(sink: SqliteEventSink) -> TeamEvalDashboard:
    return TeamEvalDashboard(sink)


def _emit_task_lifecycle(
    sink: SqliteEventSink, session_id: str, task_id: str,
    routed_layer: str = "L4_LOCAL", completed: bool = True,
) -> None:
    """Helper: emit a full task lifecycle (created → routed → completed/failed)."""
    sink.emit(OrchestratorEvent(
        event_type=EventType.TASK_CREATED, session_id=session_id, task_id=task_id,
    ))
    sink.emit(OrchestratorEvent(
        event_type=EventType.TASK_ROUTED, session_id=session_id, task_id=task_id,
        payload={"layer": routed_layer},
    ))
    if completed:
        sink.emit(OrchestratorEvent(
            event_type=EventType.TASK_COMPLETED, session_id=session_id, task_id=task_id,
            payload={"resolution_layer": routed_layer},
        ))
    else:
        sink.emit(OrchestratorEvent(
            event_type=EventType.TASK_FAILED, session_id=session_id, task_id=task_id,
        ))


# ── TeamEvalMetrics ──


class TestTeamEvalMetrics:
    def test_default_metrics_are_zero(self) -> None:
        m = TeamEvalMetrics()
        assert m.task_completion_rate == 0.0
        assert m.routing_accuracy == 0.0

    def test_to_dict_all_fields(self) -> None:
        m = TeamEvalMetrics(task_completion_rate=0.9, routing_accuracy=0.8)
        d = m.to_dict()
        assert d["task_completion_rate"] == 0.9
        assert d["routing_accuracy"] == 0.8
        assert "subagent_success_rate" in d

    def test_to_json_valid(self) -> None:
        import json
        m = TeamEvalMetrics(task_completion_rate=1.0)
        data = json.loads(m.to_json())
        assert data["task_completion_rate"] == 1.0


# ── Task Completion Rate ──


class TestTaskCompletionRate:
    def test_all_completed(self, sink: SqliteEventSink, dashboard: TeamEvalDashboard) -> None:
        for i in range(3):
            _emit_task_lifecycle(sink, "s1", f"t{i}", completed=True)
        m = dashboard.compute("s1")
        assert m.task_completion_rate == 1.0

    def test_some_failed(self, sink: SqliteEventSink, dashboard: TeamEvalDashboard) -> None:
        _emit_task_lifecycle(sink, "s1", "t1", completed=True)
        _emit_task_lifecycle(sink, "s1", "t2", completed=False)
        m = dashboard.compute("s1")
        assert m.task_completion_rate == 0.5

    def test_no_tasks(self, dashboard: TeamEvalDashboard) -> None:
        m = dashboard.compute("s1")
        assert m.task_completion_rate == 0.0


# ── Subagent Success Rate ──


class TestSubagentSuccessRate:
    def test_all_successful(self, sink: SqliteEventSink, dashboard: TeamEvalDashboard) -> None:
        for i in range(3):
            sink.emit(OrchestratorEvent(
                event_type=EventType.SUBAGENT_SPAWNED, session_id="s1", task_id=f"t{i}",
            ))
            sink.emit(OrchestratorEvent(
                event_type=EventType.SUBAGENT_COMPLETED, session_id="s1", task_id=f"t{i}",
            ))
        m = dashboard.compute("s1")
        assert m.subagent_success_rate == 1.0

    def test_some_failed(self, sink: SqliteEventSink, dashboard: TeamEvalDashboard) -> None:
        sink.emit(OrchestratorEvent(
            event_type=EventType.SUBAGENT_SPAWNED, session_id="s1",
        ))
        sink.emit(OrchestratorEvent(
            event_type=EventType.SUBAGENT_COMPLETED, session_id="s1",
        ))
        sink.emit(OrchestratorEvent(
            event_type=EventType.SUBAGENT_SPAWNED, session_id="s1",
        ))
        sink.emit(OrchestratorEvent(
            event_type=EventType.SUBAGENT_FAILED, session_id="s1",
        ))
        m = dashboard.compute("s1")
        assert m.subagent_success_rate == 0.5

    def test_no_subagents(self, dashboard: TeamEvalDashboard) -> None:
        m = dashboard.compute("s1")
        assert m.subagent_success_rate == 0.0


# ── Messages Per Task ──


class TestMessagesPerTask:
    def test_messages_per_task(self, sink: SqliteEventSink, dashboard: TeamEvalDashboard) -> None:
        sink.emit(OrchestratorEvent(
            event_type=EventType.TASK_CREATED, session_id="s1", task_id="t1",
        ))
        for _ in range(4):
            sink.emit(OrchestratorEvent(
                event_type=EventType.MESSAGE_SENT, session_id="s1", task_id="t1",
            ))
        m = dashboard.compute("s1")
        assert m.messages_per_task == 4.0


# ── Export ──


class TestExport:
    def test_export_json_valid(self, sink: SqliteEventSink, dashboard: TeamEvalDashboard) -> None:
        import json
        _emit_task_lifecycle(sink, "s1", "t1", completed=True)
        result = dashboard.export_json("s1")
        data = json.loads(result)
        assert "task_completion_rate" in data
        assert data["task_completion_rate"] == 1.0
