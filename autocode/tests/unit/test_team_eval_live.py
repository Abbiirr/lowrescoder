"""Tests for live team-runtime eval collection."""

from __future__ import annotations

import sqlite3
from unittest.mock import MagicMock

import pytest

from autocode.agent.events import (
    EventType,
    NullEventSink,
    OrchestratorEvent,
    SqliteEventSink,
)
from autocode.agent.orchestrator import Orchestrator
from autocode.eval.team_eval import LiveEvalCollector, TeamEvalMetrics
from autocode.session.models import ensure_tables
from autocode.session.task_store import TaskStore


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
def collector() -> LiveEvalCollector:
    return LiveEvalCollector()


# ── LiveEvalCollector ──


class TestLiveEvalCollector:
    def test_tracks_task_created(self, collector: LiveEvalCollector) -> None:
        collector.on_event(OrchestratorEvent(
            event_type=EventType.TASK_CREATED, session_id="s1",
        ))
        assert collector.metrics.task_completion_rate == 0.0  # created but not completed

    def test_tracks_task_completed(self, collector: LiveEvalCollector) -> None:
        collector.on_event(OrchestratorEvent(
            event_type=EventType.TASK_CREATED, session_id="s1",
        ))
        collector.on_event(OrchestratorEvent(
            event_type=EventType.TASK_COMPLETED, session_id="s1",
        ))
        assert collector.metrics.task_completion_rate == 1.0

    def test_tracks_subagent_lifecycle(self, collector: LiveEvalCollector) -> None:
        collector.on_event(OrchestratorEvent(event_type=EventType.SUBAGENT_SPAWNED))
        collector.on_event(OrchestratorEvent(event_type=EventType.SUBAGENT_COMPLETED))
        collector.on_event(OrchestratorEvent(event_type=EventType.SUBAGENT_SPAWNED))
        collector.on_event(OrchestratorEvent(event_type=EventType.SUBAGENT_FAILED))
        assert collector.metrics.subagent_success_rate == 0.5

    def test_tracks_messages_per_task(self, collector: LiveEvalCollector) -> None:
        collector.on_event(OrchestratorEvent(event_type=EventType.TASK_CREATED))
        collector.on_event(OrchestratorEvent(event_type=EventType.MESSAGE_SENT))
        collector.on_event(OrchestratorEvent(event_type=EventType.MESSAGE_SENT))
        assert collector.metrics.messages_per_task == 2.0

    def test_reset(self, collector: LiveEvalCollector) -> None:
        collector.on_event(OrchestratorEvent(event_type=EventType.TASK_CREATED))
        collector.on_event(OrchestratorEvent(event_type=EventType.TASK_COMPLETED))
        collector.reset()
        assert collector.metrics.task_completion_rate == 0.0


# ── Integration with Orchestrator ──


class TestLiveEvalWithOrchestrator:
    def test_orchestrator_dispatch_produces_events(
        self, sink: SqliteEventSink,
    ) -> None:
        collector = LiveEvalCollector()
        orch = Orchestrator(
            agent_loop=MagicMock(),
            event_sink=sink,
        )
        # Dispatch emits TASK_ROUTED
        orch.dispatch("fix bug", task_type="bugfix")
        # Manually feed events to collector (live wiring would use CompositeEventSink)
        events = sink.query(session_id="", event_type="task_routed")
        for e in events:
            collector.on_event(OrchestratorEvent(
                event_type=EventType.TASK_ROUTED,
            ))
        # At least one routing event was tracked
        assert len(events) >= 1


# ── Failure Injection ──


class TestFailureInjection:
    def test_all_tasks_fail(self, collector: LiveEvalCollector) -> None:
        for _ in range(5):
            collector.on_event(OrchestratorEvent(event_type=EventType.TASK_CREATED))
            collector.on_event(OrchestratorEvent(event_type=EventType.TASK_FAILED))
        assert collector.metrics.task_completion_rate == 0.0

    def test_all_subagents_fail(self, collector: LiveEvalCollector) -> None:
        for _ in range(3):
            collector.on_event(OrchestratorEvent(event_type=EventType.SUBAGENT_SPAWNED))
            collector.on_event(OrchestratorEvent(event_type=EventType.SUBAGENT_FAILED))
        assert collector.metrics.subagent_success_rate == 0.0
