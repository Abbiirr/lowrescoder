"""Tests for Orchestrator as sole control plane (Sprint 8D)."""

from __future__ import annotations

import sqlite3
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from autocode.agent.bus import AgentBus, AgentMessage, MessageType
from autocode.agent.events import EventType, NullEventSink, SqliteEventSink
from autocode.agent.message_store import MessageStore
from autocode.agent.orchestrator import Orchestrator
from autocode.session.models import ensure_tables
from autocode.session.task_store import TaskStore


@pytest.fixture()
def conn():
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    ensure_tables(db)
    return db


@pytest.fixture()
def task_store(conn: sqlite3.Connection) -> TaskStore:
    return TaskStore(conn, session_id="test-session")


@pytest.fixture()
def event_sink(conn: sqlite3.Connection) -> SqliteEventSink:
    return SqliteEventSink(conn)


@pytest.fixture()
def message_store(conn: sqlite3.Connection, event_sink: SqliteEventSink) -> MessageStore:
    return MessageStore(conn, session_id="test-session", event_sink=event_sink)


# ── Factory ──


class TestCreateOrchestrator:
    def test_factory_returns_orchestrator_and_stats(self) -> None:
        from autocode.agent.factory import create_orchestrator

        provider = MagicMock()
        provider.model = "test-model"

        # Minimal tool registry
        tool_registry = MagicMock()
        tool_registry.get_all.return_value = []

        approval_manager = MagicMock()
        approval_manager.mode = "suggest"

        session_store = MagicMock()
        mock_conn = sqlite3.connect(":memory:")
        mock_conn.row_factory = sqlite3.Row
        ensure_tables(mock_conn)
        session_store.get_connection.return_value = mock_conn

        orchestrator, stats = create_orchestrator(
            provider=provider,
            tool_registry=tool_registry,
            approval_manager=approval_manager,
            session_store=session_store,
            session_id="test-session",
        )

        assert isinstance(orchestrator, Orchestrator)
        assert stats is not None
        assert orchestrator.agent_loop is not None

    def test_orchestrator_has_event_sink(self) -> None:
        from autocode.agent.factory import create_orchestrator

        provider = MagicMock()
        provider.model = "test-model"
        tool_registry = MagicMock()
        tool_registry.get_all.return_value = []
        approval_manager = MagicMock()
        approval_manager.mode = "suggest"
        session_store = MagicMock()
        mock_conn = sqlite3.connect(":memory:")
        mock_conn.row_factory = sqlite3.Row
        ensure_tables(mock_conn)
        session_store.get_connection.return_value = mock_conn

        orchestrator, _ = create_orchestrator(
            provider=provider,
            tool_registry=tool_registry,
            approval_manager=approval_manager,
            session_store=session_store,
            session_id="test-session",
        )

        assert orchestrator.event_sink is not None


# ── Submit Task ──


class TestOrchestratorSubmitTask:
    def test_submit_creates_task_in_store(
        self, task_store: TaskStore, event_sink: SqliteEventSink,
    ) -> None:
        orch = Orchestrator(
            agent_loop=MagicMock(),
            task_store=task_store,
            event_sink=event_sink,
        )
        tid = orch.submit_task("Fix the login bug", description="Users can't log in")
        assert tid
        task = task_store.get_task(tid)
        assert task is not None
        assert task.title == "Fix the login bug"

    def test_submit_emits_task_created_event(
        self, task_store: TaskStore, event_sink: SqliteEventSink, conn: sqlite3.Connection,
    ) -> None:
        orch = Orchestrator(
            agent_loop=MagicMock(),
            task_store=task_store,
            event_sink=event_sink,
        )
        orch.submit_task("Test task")
        events = event_sink.query(event_type="task_created")
        assert len(events) == 1

    def test_submit_returns_task_id(
        self, task_store: TaskStore, event_sink: SqliteEventSink,
    ) -> None:
        orch = Orchestrator(
            agent_loop=MagicMock(),
            task_store=task_store,
            event_sink=event_sink,
        )
        tid = orch.submit_task("Task")
        assert isinstance(tid, str)
        assert len(tid) > 0


# ── Dispatch Integration ──


class TestOrchestratorDispatchIntegration:
    def test_dispatch_with_event_sink(
        self, event_sink: SqliteEventSink,
    ) -> None:
        orch = Orchestrator(
            agent_loop=MagicMock(),
            event_sink=event_sink,
        )
        result = orch.dispatch("fix bug", task_type="bugfix")
        assert result["success"] is True
        # Should emit TASK_ROUTED event
        events = event_sink.query(event_type="task_routed")
        assert len(events) == 1

    def test_dispatch_records_cost(self) -> None:
        orch = Orchestrator(agent_loop=MagicMock())
        orch.dispatch("task", task_type="general")
        assert orch.cost.total_tokens > 0


# ── Backward Compatibility ──


class TestOrchestratorBackwardCompat:
    def test_existing_constructor_still_works(self) -> None:
        """Old-style Orchestrator() without agent_loop still functions."""
        orch = Orchestrator()
        assert orch.bus is not None
        assert orch.router is not None
        assert orch.cost is not None

    def test_route_task_still_works(self) -> None:
        orch = Orchestrator()
        decision = orch.route_task("code_edit", complexity="medium")
        assert decision is not None

    def test_dispatch_without_agent_loop(self) -> None:
        orch = Orchestrator()
        result = orch.dispatch("test task", task_type="general")
        assert result["success"] is True

    def test_summary_property(self) -> None:
        orch = Orchestrator()
        s = orch.summary
        assert "Orchestrator Summary" in s

    def test_agent_loop_property_none_when_not_set(self) -> None:
        orch = Orchestrator()
        assert orch.agent_loop is None


# ── Agent Loop Access ──


class TestOrchestratorAgentLoopAccess:
    def test_agent_loop_property(self) -> None:
        mock_loop = MagicMock()
        orch = Orchestrator(agent_loop=mock_loop)
        assert orch.agent_loop is mock_loop

    def test_session_id_property(self, event_sink: SqliteEventSink) -> None:
        orch = Orchestrator(
            agent_loop=MagicMock(),
            event_sink=event_sink,
            session_id="s1",
        )
        assert orch.session_id == "s1"

    def test_session_id_setter_propagates_to_loop(self) -> None:
        mock_loop = MagicMock()
        orch = Orchestrator(agent_loop=mock_loop, session_id="s1")
        orch.session_id = "s2"
        assert orch.session_id == "s2"
        assert mock_loop.session_id == "s2"

    def test_cancel_delegates_to_loop(self) -> None:
        mock_loop = MagicMock()
        orch = Orchestrator(agent_loop=mock_loop)
        orch.cancel()
        mock_loop.cancel.assert_called_once()

    def test_cancel_no_loop_is_noop(self) -> None:
        orch = Orchestrator()
        orch.cancel()  # should not raise

    def test_set_mode_delegates_to_loop(self) -> None:
        mock_loop = MagicMock()
        orch = Orchestrator(agent_loop=mock_loop)
        orch.set_mode("planning")
        mock_loop.set_mode.assert_called_once_with("planning")

    def test_get_mode_delegates_to_loop(self) -> None:
        mock_loop = MagicMock()
        mock_loop.get_mode.return_value = "auto"
        orch = Orchestrator(agent_loop=mock_loop)
        assert orch.get_mode() == "auto"

    @pytest.mark.asyncio
    async def test_run_delegates_to_loop(self) -> None:
        mock_loop = MagicMock()
        mock_loop.run = AsyncMock(return_value="response")
        orch = Orchestrator(agent_loop=mock_loop)
        result = await orch.run("hello")
        mock_loop.run.assert_called_once_with("hello")
        assert result == "response"

    @pytest.mark.asyncio
    async def test_run_without_loop_raises(self) -> None:
        orch = Orchestrator()
        with pytest.raises(RuntimeError, match="No AgentLoop"):
            await orch.run("hello")
