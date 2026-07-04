"""Direct unit tests for backend chat execution outside BackendServer."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from autocode.agent.completion import SessionStats
from autocode.agent.cost_dashboard import CostDashboard
from autocode.agent.token_tracker import TokenTracker
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
        self._show_thinking = False
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

    @property
    def session_log_dir(self):
        return self.__dict__["_session_log_dir"]

    @session_log_dir.setter
    def session_log_dir(self, value):
        self.__dict__["_session_log_dir"] = value

    @property
    def session_titled(self):
        return self.__dict__["_session_titled"]

    @session_titled.setter
    def session_titled(self, value):
        self.__dict__["_session_titled"] = value

    @property
    def session_stats(self):
        return self.__dict__["_session_stats"]

    @session_stats.setter
    def session_stats(self, value):
        self.__dict__["_session_stats"] = value

    @property
    def session_approved_tools(self):
        return self.__dict__["_session_approved_tools"]

    @property
    def approval_manager(self):
        return self.__dict__["_approval_manager"]

    @property
    def context_assembler(self):
        return self.__dict__["_context_assembler"]

    @property
    def l3_provider(self):
        return self.__dict__["_l3_provider"]

    @property
    def task_store(self):
        return self.__dict__["_task_store"]

    @task_store.setter
    def task_store(self, value):
        self.__dict__["_task_store"] = value

    @property
    def subagent_manager(self):
        return self.__dict__["_subagent_manager"]

    @property
    def edit_count(self):
        return self.__dict__["_edit_count"]

    @edit_count.setter
    def edit_count(self, value):
        self.__dict__["_edit_count"] = value

    @property
    def show_thinking(self):
        return self.__dict__["_show_thinking"]

    def emit_cost_update(self) -> None:
        self.__dict__["_emit_cost_update"]()

    async def teardown_agent_resources(self) -> None:
        await self.__dict__["_teardown_agent_resources"]()

    def ensure_agent_loop(self):
        return self.__dict__["_ensure_agent_loop"]()

    def expand_file_mentions(self, message: str) -> str:
        return self.__dict__["_expand_file_mentions"](message)

    def select_chat_layer(self, message: str):
        return self.__dict__["_select_chat_layer"](message)

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


@pytest.mark.asyncio
@pytest.mark.parametrize(("show_thinking", "expected"), [(False, False), (True, True)])
async def test_show_thinking_propagates_to_agent_loop_reasoning(
    show_thinking: bool,
    expected: bool,
) -> None:
    host = FakeHost()
    host._show_thinking = show_thinking

    await backend_chat.run_chat_turn(
        host,
        message="hello",
        session_id=None,
        request_id=7,
    )

    assert host.agent_loop.run.await_args.kwargs["reasoning_enabled"] is expected


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


@pytest.mark.asyncio
async def test_cost_warning_emitted_once_per_session() -> None:
    host = FakeHost()
    dashboard = CostDashboard()
    tracker = TokenTracker(cost_dashboard=dashboard, cost_limit_usd=0.001)
    stats = SessionStats()
    stats.token_tracker = tracker
    host._session_stats = stats

    async def run_with_cost_record(_message: str, **_kwargs: object) -> None:
        tracker.record(prompt_tokens=500, completion_tokens=0, provider="openrouter")

    host.agent_loop.run = AsyncMock(side_effect=run_with_cost_record)

    await backend_chat.run_chat_turn(
        host,
        message="first",
        session_id=None,
        request_id=10,
    )
    await backend_chat.run_chat_turn(
        host,
        message="second",
        session_id=None,
        request_id=11,
    )

    warnings = [
        params["message"]
        for method, params in host.notifications
        if method == "on_warning"
        and "Session cost limit reached" in str(params["message"])
    ]
    assert warnings == [
        "Session cost limit reached: $0.0015 / $0.0010 threshold. Continuing; use /cost to view."
    ]


@pytest.mark.asyncio
async def test_cost_warning_includes_total_and_threshold() -> None:
    """Cost warnings include the observed total and configured threshold."""
    host = FakeHost()
    dashboard = CostDashboard()
    tracker = TokenTracker(cost_dashboard=dashboard, cost_limit_usd=0.002)
    stats = SessionStats()
    stats.token_tracker = tracker
    host._session_stats = stats

    async def run_with_cost_record(_message: str, **_kwargs: object) -> None:
        tracker.record(prompt_tokens=1_000, completion_tokens=0, provider="openrouter")

    host.agent_loop.run = AsyncMock(side_effect=run_with_cost_record)

    await backend_chat.run_chat_turn(
        host,
        message="first",
        session_id=None,
        request_id=12,
    )

    assert (
        "Session cost limit reached: $0.0030 / $0.0020 threshold. Continuing; use /cost to view."
        in [
            params["message"]
            for method, params in host.notifications
            if method == "on_warning"
        ]
    )


class PublicOnlyHost(FakeHost):
    @property
    def session_log_dir(self):
        return self.__dict__["_session_log_dir"]

    @session_log_dir.setter
    def session_log_dir(self, value):
        self.__dict__["_session_log_dir"] = value

    @property
    def session_titled(self):
        return self.__dict__["_session_titled"]

    @session_titled.setter
    def session_titled(self, value):
        self.__dict__["_session_titled"] = value

    @property
    def session_stats(self):
        return self.__dict__["_session_stats"]

    @session_stats.setter
    def session_stats(self, value):
        self.__dict__["_session_stats"] = value

    @property
    def session_approved_tools(self):
        return self.__dict__["_session_approved_tools"]

    @property
    def approval_manager(self):
        return self.__dict__["_approval_manager"]

    @property
    def context_assembler(self):
        return self.__dict__["_context_assembler"]

    @property
    def l3_provider(self):
        return self.__dict__["_l3_provider"]

    @property
    def task_store(self):
        return self.__dict__["_task_store"]

    @task_store.setter
    def task_store(self, value):
        self.__dict__["_task_store"] = value

    @property
    def subagent_manager(self):
        return self.__dict__["_subagent_manager"]

    @property
    def edit_count(self):
        return self.__dict__["_edit_count"]

    @edit_count.setter
    def edit_count(self, value):
        self.__dict__["_edit_count"] = value

    @property
    def show_thinking(self):
        return self.__dict__["_show_thinking"]

    def emit_cost_update(self) -> None:
        self.__dict__["_emit_cost_update"]()

    async def teardown_agent_resources(self) -> None:
        await self.__dict__["_teardown_agent_resources"]()

    def ensure_agent_loop(self):
        return self.__dict__["_ensure_agent_loop"]()

    def expand_file_mentions(self, message: str) -> str:
        return self.__dict__["_expand_file_mentions"](message)

    def select_chat_layer(self, message: str):
        return self.__dict__["_select_chat_layer"](message)

    def __getattribute__(self, name: str):
        if name.startswith("_") and name not in {
            "__class__",
            "__dict__",
            "__getattribute__",
            "__init__",
            "_run_agent_loop",
        }:
            raise AssertionError(f"chat service accessed private host member: {name}")
        return super().__getattribute__(name)


@pytest.mark.asyncio
async def test_run_chat_turn_uses_public_chat_host_surface_only() -> None:
    host = PublicOnlyHost()

    await backend_chat.run_chat_turn(
        host,
        message="hello",
        session_id=None,
        request_id=13,
    )

    assert [method for method, _params in host.notifications][0] == "on_chat_ack"
