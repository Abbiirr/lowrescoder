"""Direct unit tests for backend chat execution outside BackendServer."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from autocode.backend import chat as backend_chat


class FakeHost:
    def __init__(self) -> None:
        self.config = SimpleNamespace(
            logging=MagicMock(),
            layer2=SimpleNamespace(search_top_k=3),
        )
        self.project_root = MagicMock()
        self.session_store = MagicMock()
        self.session_id = "session-1"
        self._session_log_dir = MagicMock()
        self._session_titled = False
        self._session_stats = None
        self._session_approved_tools: set[str] = set()
        self._approval_manager = MagicMock()
        self._context_assembler = None
        self._l3_provider = None
        self._task_store = None
        self._subagent_manager = None
        self._edit_count = 0
        self.notifications: list[tuple[str, dict[str, object]]] = []
        self.emit_request = AsyncMock(return_value={})
        self._emit_cost_update = MagicMock()
        self._teardown_agent_resources = AsyncMock()
        self._expand_file_mentions = MagicMock(side_effect=lambda message: message)
        self._select_chat_layer = MagicMock(return_value=(4, "complex_task", False))
        self.agent_loop = MagicMock()
        self.agent_loop.run = AsyncMock(side_effect=self._run_agent_loop)
        self._ensure_agent_loop = MagicMock(return_value=self.agent_loop)

    def emit_notification(self, method: str, params: dict[str, object]) -> None:
        self.notifications.append((method, params))

    async def _run_agent_loop(self, message: str, **kwargs: object) -> None:
        on_chunk = kwargs["on_chunk"]
        on_thinking_chunk = kwargs["on_thinking_chunk"]
        on_retry_notice = kwargs["on_retry_notice"]
        on_tool_call = kwargs["on_tool_call"]
        on_retry_notice("WARNING: gateway still warming")
        on_chunk("hello")
        on_thinking_chunk("thinking")
        on_tool_call("read_file", "completed", "contents")


@pytest.mark.asyncio
async def test_run_chat_turn_is_directly_testable_without_backend_server() -> None:
    host = FakeHost()

    await backend_chat.run_chat_turn(
        host,
        message="hello",
        session_id=None,
        request_id=7,
    )

    methods = [method for method, _params in host.notifications]
    assert methods[0] == "on_chat_ack"
    assert "on_warning" in methods
    assert "on_token" in methods
    assert "on_thinking" in methods
    assert methods[-1] == "on_done"
    host.session_store.update_session.assert_called_once_with("session-1", title="hello")
    host._ensure_agent_loop.assert_called_once()
    host.agent_loop.run.assert_awaited_once()


def test_on_tool_call_emits_task_state_for_task_tools() -> None:
    host = FakeHost()
    task = MagicMock()
    task.model_dump.return_value = {"id": "t1", "title": "Task", "status": "open"}
    host._task_store = MagicMock()
    host._task_store.list_tasks.return_value = [task]
    host._subagent_manager = MagicMock()
    host._subagent_manager.list_all.return_value = [{"id": "s1", "status": "running"}]

    backend_chat.on_tool_call(host, "create_task", "completed", "created")

    assert host.notifications[0][0] == "on_tool_call"
    assert host.notifications[1] == (
        "on_task_state",
        {
            "tasks": [{"id": "t1", "title": "Task", "status": "open"}],
            "subagents": [{"id": "s1", "status": "running"}],
        },
    )


@pytest.mark.asyncio
async def test_approval_callback_uses_session_auto_approve_before_transport_roundtrip() -> None:
    host = FakeHost()
    host._session_approved_tools.add("run_command")

    approved = await backend_chat.approval_callback(host, "run_command", {"cmd": "pytest"})

    assert approved is True
    host.emit_request.assert_not_awaited()
    host._approval_manager.enable_shell.assert_called_once()
    assert host.notifications[0] == (
        "on_tool_call",
        {"name": "run_command", "status": "pending", "result": "(auto-approved)"},
    )
