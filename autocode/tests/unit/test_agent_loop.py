"""Tests for the agent loop."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any
from unittest.mock import ANY, AsyncMock, Mock

import pytest

from autocode.agent.approval import ApprovalManager, ApprovalMode
from autocode.agent.context import ContextEngine
from autocode.agent.delegation import DelegationPolicy
from autocode.agent.hooks import HookEvent
from autocode.agent.loop import AgentLoop, encode_tool_termination
from autocode.agent.middleware import MiddlewareStack, create_default_middleware
from autocode.agent.prompts import (
    SYSTEM_PROMPT,
    build_dynamic_suffix,
    build_static_prefix,
    build_system_prompt,
)
from autocode.agent.subagent import LLMScheduler, SubagentManager
from autocode.agent.subagent_tools import register_subagent_tools
from autocode.agent.task_tools import register_task_tools
from autocode.agent.tool_result_cache import ToolResultCache
from autocode.agent.tools import ToolDefinition, ToolRegistry, create_default_registry
from autocode.config import ShellConfig
from autocode.layer4.llm import LLMResponse, ToolCall
from autocode.session.store import SessionStore
from autocode.session.task_store import TaskStore


@pytest.fixture()
def store(tmp_path: Path) -> SessionStore:
    s = SessionStore(tmp_path / "test.db")
    yield s
    s.close()


@pytest.fixture()
def session_id(store: SessionStore, tmp_path: Path) -> str:
    return store.create_session(
        title="Test", model="m", provider="mock",
        project_dir=str(tmp_path),
    )


def _make_mock_provider(responses: list[LLMResponse]) -> Any:
    """Create a mock provider that returns responses in sequence."""
    mock = AsyncMock()
    call_count = 0

    async def fake_generate_with_tools(messages: Any, tools: Any, **kwargs: Any) -> LLMResponse:
        nonlocal call_count
        idx = min(call_count, len(responses) - 1)
        call_count += 1
        resp = responses[idx]
        on_chunk = kwargs.get("on_chunk")
        if on_chunk and resp.content:
            on_chunk(resp.content)
        return resp

    mock.generate_with_tools = fake_generate_with_tools
    return mock


class TestAgentLoop:
    @pytest.mark.asyncio()
    async def test_text_only_response(self, store: SessionStore, session_id: str) -> None:
        """A text-only LLM response returns immediately."""
        provider = _make_mock_provider([LLMResponse(content="Hello!")])
        registry = ToolRegistry()
        approval = ApprovalManager(ApprovalMode.SUGGEST)

        loop = AgentLoop(provider, registry, approval, store, session_id)
        result = await loop.run("Hi")

        assert result == "Hello!"
        messages = store.get_messages(session_id)
        assert any(m.content == "Hi" for m in messages)
        assert any(m.content == "Hello!" for m in messages)

    @pytest.mark.asyncio()
    async def test_cost_dashboard_uses_provider_model_label(
        self,
        store: SessionStore,
        session_id: str,
    ) -> None:
        """Cost details should group live gateway usage by provider/model, not class name."""
        from autocode.agent.cost_dashboard import CostDashboard
        from autocode.agent.token_tracker import TokenTracker

        provider = _make_mock_provider([
            LLMResponse(
                content="OK",
                usage={
                    "prompt_tokens": 100,
                    "completion_tokens": 25,
                    "cached_input_tokens": 0,
                },
            )
        ])
        provider.api_base = "http://localhost:4000/v1"
        provider.model = "coding"
        dashboard = CostDashboard()
        tracker = TokenTracker(cost_dashboard=dashboard)
        loop = AgentLoop(
            provider,
            ToolRegistry(),
            ApprovalManager(ApprovalMode.SUGGEST),
            store,
            session_id,
            token_tracker=tracker,
        )

        await loop.run("Hi")

        assert "openrouter / coding" in dashboard.by_provider_model()

    @pytest.mark.asyncio()
    async def test_reasoning_disabled_overrides_middleware_budget(
        self,
        store: SessionStore,
        session_id: str,
    ) -> None:
        """A user-disabled thinking toggle must force provider reasoning off."""
        reasoning_flags: list[bool] = []

        async def fake_generate_with_tools(
            messages: Any,
            tools: Any,
            **kwargs: Any,
        ) -> LLMResponse:
            reasoning_flags.append(bool(kwargs.get("reasoning_enabled", True)))
            return LLMResponse(content="No thinking")

        provider = AsyncMock()
        provider.generate_with_tools = fake_generate_with_tools
        loop = AgentLoop(
            provider,
            ToolRegistry(),
            ApprovalManager(ApprovalMode.SUGGEST),
            store,
            session_id,
            middleware=create_default_middleware(),
        )

        result = await loop.run("Hi", reasoning_enabled=False)

        assert result == "No thinking"
        assert reasoning_flags == [False]

    @pytest.mark.asyncio()
    async def test_single_tool_call_and_response(
        self, store: SessionStore, session_id: str, tmp_path: Path,
    ) -> None:
        """Tool call is executed and result is fed back to LLM."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("file contents")

        tool_response = LLMResponse(
            content="",
            tool_calls=[ToolCall(id="tc1", name="read_file", arguments={"path": str(test_file)})],
        )
        final_response = LLMResponse(content="I read the file. It says: file contents")

        provider = _make_mock_provider([tool_response, final_response])
        registry = create_default_registry()
        approval = ApprovalManager(ApprovalMode.AUTO)

        loop = AgentLoop(provider, registry, approval, store, session_id)
        result = await loop.run("Read test.txt")

        assert "file contents" in result

    @pytest.mark.asyncio()
    async def test_post_tool_use_hook_fires_after_successful_tool_execution(
        self, store: SessionStore, session_id: str,
    ) -> None:
        """PostToolUse receives execution metadata after a tool completes."""
        registry = ToolRegistry()
        registry.register(ToolDefinition(
            name="echo_tool",
            description="Echo a value.",
            parameters={"type": "object", "properties": {"value": {"type": "string"}}},
            handler=lambda value: f"echo:{value}",
        ))
        hook_registry = Mock()
        hook_registry.fire.return_value = []
        loop = AgentLoop(
            provider=AsyncMock(),
            tool_registry=registry,
            approval_manager=ApprovalManager(ApprovalMode.AUTO),
            session_store=store,
            session_id=session_id,
            hook_registry=hook_registry,
        )
        msg_id = store.add_message(session_id, "assistant", "")

        result = await loop._execute_tool_call(
            ToolCall(id="tc1", name="echo_tool", arguments={"value": "hello"}),
            msg_id=msg_id,
        )

        assert result[0] == "echo:hello"
        hook_registry.fire.assert_any_call(
            HookEvent.POST_TOOL_USE,
            {
                "session_id": session_id,
                "arguments": {"value": "hello"},
                "status": "completed",
                "result_preview": "echo:hello",
                "duration_ms": ANY,
            },
            tool_name="echo_tool",
        )

    @pytest.mark.asyncio()
    async def test_interruptible_async_tool_is_drained_on_cancellation(
        self,
        store: SessionStore,
        session_id: str,
    ) -> None:
        """Cancelled async tool handlers are awaited so coroutine warnings do not leak."""
        started = asyncio.Event()
        cleaned_up = asyncio.Event()

        async def slow_tool() -> str:
            started.set()
            try:
                await asyncio.sleep(60)
            finally:
                cleaned_up.set()
            return "unreachable"

        registry = ToolRegistry()
        registry.register(ToolDefinition(
            name="slow_tool",
            description="Slow async tool.",
            parameters={"type": "object", "properties": {}},
            handler=slow_tool,
            interruptible=True,
        ))
        loop = AgentLoop(
            provider=AsyncMock(),
            tool_registry=registry,
            approval_manager=ApprovalManager(ApprovalMode.AUTO),
            session_store=store,
            session_id=session_id,
        )
        tool = registry.get("slow_tool")
        assert tool is not None

        task = asyncio.create_task(loop._invoke_tool_handler(tool, {}))
        await started.wait()

        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

        assert cleaned_up.is_set()

    @pytest.mark.asyncio()
    async def test_large_tool_result_is_recorded_in_tool_result_cache(
        self, store: SessionStore, session_id: str,
    ) -> None:
        """Large completed tool outputs should be available for selective clearing."""
        cache = ToolResultCache()
        registry = ToolRegistry()
        registry.register(ToolDefinition(
            name="large_tool",
            description="Return a large result.",
            parameters={"type": "object", "properties": {}},
            handler=lambda: "x" * 1500,
        ))
        loop = AgentLoop(
            provider=AsyncMock(),
            tool_registry=registry,
            approval_manager=ApprovalManager(ApprovalMode.AUTO),
            session_store=store,
            session_id=session_id,
            tool_result_cache=cache,
        )
        msg_id = store.add_message(session_id, "assistant", "")

        result = await loop._execute_tool_call(
            ToolCall(id="tc1", name="large_tool", arguments={}),
            msg_id=msg_id,
        )

        assert result[0] == "x" * 1500
        live_entries = cache.live_entries()
        assert len(live_entries) == 1
        assert live_entries[0].tool == "large_tool"
        assert live_entries[0].result == "x" * 1500

    @pytest.mark.asyncio()
    async def test_cache_management_tool_result_is_not_cached(
        self, store: SessionStore, session_id: str,
    ) -> None:
        """The cache management tools must not pollute the cache they inspect."""
        cache = ToolResultCache()
        cache.record("read_file", {"path": "a.py"}, "x" * 1500)
        registry = create_default_registry(project_root="", tool_result_cache=cache)
        loop = AgentLoop(
            provider=AsyncMock(),
            tool_registry=registry,
            approval_manager=ApprovalManager(ApprovalMode.AUTO),
            session_store=store,
            session_id=session_id,
            tool_result_cache=cache,
        )
        msg_id = store.add_message(session_id, "assistant", "")

        result = await loop._execute_tool_call(
            ToolCall(id="tc1", name="list_tool_results", arguments={}),
            msg_id=msg_id,
        )

        assert "read_file" in result[0]
        assert [entry.tool for entry in cache.live_entries()] == ["read_file"]

    @pytest.mark.asyncio()
    async def test_tool_output_budget_controls_truncation(
        self, store: SessionStore, session_id: str,
    ) -> None:
        """AgentLoop should honor ToolDefinition.output_budget_tokens."""
        registry = ToolRegistry()
        registry.register(ToolDefinition(
            name="small_budget_tool",
            description="Return output larger than its declared budget.",
            parameters={"type": "object", "properties": {}},
            handler=lambda: "x" * 1000,
            output_budget_tokens=20,
        ))
        loop = AgentLoop(
            provider=AsyncMock(),
            tool_registry=registry,
            approval_manager=ApprovalManager(ApprovalMode.AUTO),
            session_store=store,
            session_id=session_id,
            context_engine=ContextEngine(
                provider=None,
                session_store=store,
            ),
        )
        msg_id = store.add_message(session_id, "assistant", "")

        result = await loop._execute_tool_call(
            ToolCall(id="tc1", name="small_budget_tool", arguments={}),
            msg_id=msg_id,
        )

        assert len(result[0]) < 1000
        assert "omitted" in result[0]

    @pytest.mark.asyncio()
    async def test_post_tool_use_hook_fires_after_tool_execution_error(
        self, store: SessionStore, session_id: str,
    ) -> None:
        """PostToolUse receives error metadata when an executed tool fails."""
        def fail_tool(value: str) -> str:
            raise RuntimeError(f"boom:{value}")

        registry = ToolRegistry()
        registry.register(ToolDefinition(
            name="fail_tool",
            description="Raise an error.",
            parameters={"type": "object", "properties": {"value": {"type": "string"}}},
            handler=fail_tool,
        ))
        hook_registry = Mock()
        hook_registry.fire.return_value = []
        loop = AgentLoop(
            provider=AsyncMock(),
            tool_registry=registry,
            approval_manager=ApprovalManager(ApprovalMode.AUTO),
            session_store=store,
            session_id=session_id,
            hook_registry=hook_registry,
        )
        msg_id = store.add_message(session_id, "assistant", "")

        result = await loop._execute_tool_call(
            ToolCall(id="tc1", name="fail_tool", arguments={"value": "hello"}),
            msg_id=msg_id,
        )

        assert result[0] == "Error: boom:hello"
        hook_registry.fire.assert_any_call(
            HookEvent.POST_TOOL_USE,
            {
                "session_id": session_id,
                "arguments": {"value": "hello"},
                "status": "error",
                "result_preview": "Error: boom:hello",
                "duration_ms": ANY,
            },
            tool_name="fail_tool",
        )

    @pytest.mark.asyncio()
    async def test_cancel_interrupts_interruptible_tool_execution(
        self, store: SessionStore, session_id: str,
    ) -> None:
        """Interruptible tools receive cancellation and persist cancelled status."""
        started = asyncio.Event()
        cancelled = asyncio.Event()

        async def slow_tool() -> str:
            started.set()
            try:
                await asyncio.sleep(30)
            except asyncio.CancelledError:
                cancelled.set()
                raise

        registry = ToolRegistry()
        registry.register(ToolDefinition(
            name="slow_tool",
            description="Slow interruptible tool.",
            parameters={"type": "object", "properties": {}},
            handler=slow_tool,
            interruptible=True,
        ))
        loop = AgentLoop(
            provider=AsyncMock(),
            tool_registry=registry,
            approval_manager=ApprovalManager(ApprovalMode.AUTO),
            session_store=store,
            session_id=session_id,
        )
        msg_id = store.add_message(session_id, "assistant", "")
        tool_events: list[tuple[str, str, str]] = []

        task = asyncio.create_task(loop._execute_tool_call(
            ToolCall(id="tc1", name="slow_tool", arguments={}),
            msg_id=msg_id,
            on_tool_call=lambda name, status, result: tool_events.append(
                (name, status, result)
            ),
        ))
        await asyncio.wait_for(started.wait(), timeout=1)

        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

        assert cancelled.is_set()
        row = store._conn.execute(
            "SELECT status, result FROM tool_calls WHERE tool_name = 'slow_tool'"
        ).fetchone()
        assert row["status"] == "cancelled"
        assert "cancelled" in row["result"].lower()
        assert ("slow_tool", "cancelled", "Tool call cancelled.") in tool_events

    @pytest.mark.asyncio()
    async def test_cancel_waits_for_non_interruptible_tool_execution(
        self, store: SessionStore, session_id: str,
    ) -> None:
        """Non-interruptible tools finish and persist completion before cancellation propagates."""
        started = asyncio.Event()
        may_finish = asyncio.Event()
        finished = asyncio.Event()

        async def write_like_tool() -> str:
            started.set()
            await may_finish.wait()
            finished.set()
            return "written"

        registry = ToolRegistry()
        registry.register(ToolDefinition(
            name="write_like_tool",
            description="Non-interruptible write-like tool.",
            parameters={"type": "object", "properties": {}},
            handler=write_like_tool,
            interruptible=False,
            mutates_fs=True,
        ))
        loop = AgentLoop(
            provider=AsyncMock(),
            tool_registry=registry,
            approval_manager=ApprovalManager(ApprovalMode.AUTO),
            session_store=store,
            session_id=session_id,
        )
        msg_id = store.add_message(session_id, "assistant", "")
        tool_events: list[tuple[str, str, str]] = []

        task = asyncio.create_task(loop._execute_tool_call(
            ToolCall(id="tc1", name="write_like_tool", arguments={}),
            msg_id=msg_id,
            on_tool_call=lambda name, status, result: tool_events.append(
                (name, status, result)
            ),
        ))
        await asyncio.wait_for(started.wait(), timeout=1)

        task.cancel()
        may_finish.set()
        with pytest.raises(asyncio.CancelledError):
            await task

        assert finished.is_set()
        row = store._conn.execute(
            "SELECT status, result FROM tool_calls WHERE tool_name = 'write_like_tool'"
        ).fetchone()
        assert row["status"] == "completed"
        assert row["result"] == "written"
        assert ("write_like_tool", "completed", "written") in tool_events

    @pytest.mark.asyncio()
    async def test_cancel_interrupts_default_run_command(
        self, store: SessionStore, session_id: str,
    ) -> None:
        """The default run_command path is interruptible and records cancellation."""
        registry = create_default_registry()
        approval = ApprovalManager(
            ApprovalMode.AUTONOMOUS,
            ShellConfig(enabled=True),
        )
        loop = AgentLoop(
            provider=AsyncMock(),
            tool_registry=registry,
            approval_manager=approval,
            session_store=store,
            session_id=session_id,
        )
        msg_id = store.add_message(session_id, "assistant", "")
        running = asyncio.Event()

        def on_tool_call(name: str, status: str, _result: str) -> None:
            if name == "run_command" and status == "running":
                running.set()

        task = asyncio.create_task(loop._execute_tool_call(
            ToolCall(
                id="tc1",
                name="run_command",
                arguments={
                    "command": f"{sys.executable} -c 'import time; time.sleep(30)'",
                    "timeout": 30,
                },
            ),
            msg_id=msg_id,
            on_tool_call=on_tool_call,
        ))
        await asyncio.wait_for(running.wait(), timeout=1)

        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

        row = store._conn.execute(
            "SELECT status, result FROM tool_calls WHERE tool_name = 'run_command'"
        ).fetchone()
        assert row["status"] == "cancelled"
        assert "cancelled" in row["result"].lower()

    @pytest.mark.asyncio()
    async def test_tool_termination_signal_stops_loop(
        self, store: SessionStore, session_id: str,
    ) -> None:
        """A tool can terminate the loop with a final response."""
        tool_response = LLMResponse(
            content="",
            tool_calls=[ToolCall(id="tc1", name="done_tool", arguments={})],
        )

        provider = AsyncMock()
        provider.generate_with_tools = AsyncMock(return_value=tool_response)

        registry = ToolRegistry()
        registry.register(ToolDefinition(
            name="done_tool",
            description="Return a completed benchmark result.",
            parameters={"type": "object", "properties": {}, "required": []},
            handler=lambda: encode_tool_termination(
                "PASSED\nAll checks passed",
                "Benchmark verification passed. Stop editing and report the fix briefly.",
            ),
        ))
        approval = ApprovalManager(ApprovalMode.AUTO)

        loop = AgentLoop(provider, registry, approval, store, session_id)
        result = await loop.run("finish after tool")

        assert result == "Benchmark verification passed. Stop editing and report the fix briefly."
        assert provider.generate_with_tools.await_count == 1

    @pytest.mark.asyncio()
    async def test_max_iterations_stops(self, store: SessionStore, session_id: str) -> None:
        """Loop stops after MAX_ITERATIONS even if tools keep being called."""
        # Every response has a tool call, never returns text
        tool_response = LLMResponse(
            content="still going",
            tool_calls=[ToolCall(id="tc1", name="unknown_tool", arguments={})],
        )

        provider = _make_mock_provider([tool_response] * 15)
        registry = ToolRegistry()
        approval = ApprovalManager(ApprovalMode.AUTO)

        loop = AgentLoop(provider, registry, approval, store, session_id)
        loop.MAX_ITERATIONS = 3
        result = await loop.run("infinite loop test")
        # Should stop and return something (either content or max iterations message)
        assert result is not None

    @pytest.mark.asyncio()
    async def test_tool_error_propagated(self, store: SessionStore, session_id: str) -> None:
        """Tool execution errors are returned as tool results."""
        tool_response = LLMResponse(
            content="",
            tool_calls=[ToolCall(
                id="tc1", name="read_file", arguments={"path": "/nonexistent/file"},
            )],
        )
        final_response = LLMResponse(content="File not found.")

        provider = _make_mock_provider([tool_response, final_response])
        registry = create_default_registry()
        approval = ApprovalManager(ApprovalMode.AUTO)

        loop = AgentLoop(provider, registry, approval, store, session_id)
        result = await loop.run("Read missing file")
        assert result is not None

    @pytest.mark.asyncio()
    async def test_cancellation(self, store: SessionStore, session_id: str) -> None:
        """Cancelled loop returns early."""
        # Provider that cancels the loop during execution
        async def cancelling_generate(messages: Any, tools: Any, **kwargs: Any) -> LLMResponse:
            loop.cancel()
            return LLMResponse(
                content="",
                tool_calls=[ToolCall(id="tc1", name="read_file", arguments={"path": "x"})],
            )

        mock = AsyncMock()
        mock.generate_with_tools = cancelling_generate

        registry = ToolRegistry()
        approval = ApprovalManager(ApprovalMode.SUGGEST)

        loop = AgentLoop(mock, registry, approval, store, session_id)
        result = await loop.run("test")
        assert result == "[Cancelled]"

    @pytest.mark.asyncio()
    async def test_messages_persisted_to_session(
        self, store: SessionStore, session_id: str,
    ) -> None:
        """Messages are stored in the session store."""
        provider = _make_mock_provider([LLMResponse(content="Stored response")])
        registry = ToolRegistry()
        approval = ApprovalManager(ApprovalMode.SUGGEST)

        loop = AgentLoop(provider, registry, approval, store, session_id)
        await loop.run("Persist this")

        messages = store.get_messages(session_id)
        roles = [m.role for m in messages]
        assert "user" in roles
        assert "assistant" in roles

    @pytest.mark.asyncio()
    async def test_reasoning_budget_passes_high_low_flags_to_provider(
        self, store: SessionStore, session_id: str, tmp_path: Path,
    ) -> None:
        """Middleware should send high/low reasoning flags across iterations."""
        test_file = tmp_path / "sample.txt"
        test_file.write_text("hello")

        responses = [
            LLMResponse(
                content="",
                tool_calls=[
                    ToolCall(
                        id="tc1",
                        name="read_file",
                        arguments={"path": str(test_file)},
                    ),
                ],
            ),
            LLMResponse(content="Done reading."),
        ]
        reasoning_flags: list[bool] = []

        async def fake_generate_with_tools(messages: Any, tools: Any, **kwargs: Any) -> LLMResponse:
            reasoning_flags.append(bool(kwargs.get("reasoning_enabled", True)))
            return responses[min(len(reasoning_flags) - 1, len(responses) - 1)]

        provider = AsyncMock()
        provider.generate_with_tools = fake_generate_with_tools
        registry = create_default_registry()
        approval = ApprovalManager(ApprovalMode.AUTO)

        loop = AgentLoop(
            provider,
            registry,
            approval,
            store,
            session_id,
            middleware=create_default_middleware(),
        )
        result = await loop.run("Read sample.txt")

        assert result == "Done reading."
        assert reasoning_flags[:2] == [True, False]


class TestAskUserTool:
    """Tests for the ask_user tool integration in the agent loop."""

    @pytest.mark.asyncio()
    async def test_ask_user_with_callback(
        self, store: SessionStore, session_id: str,
    ) -> None:
        """ask_user tool call routes to ask_user_callback."""
        tool_response = LLMResponse(
            content="",
            tool_calls=[ToolCall(
                id="tc1", name="ask_user",
                arguments={"question": "Which framework?", "options": ["Django", "Flask"]},
            )],
        )
        final_response = LLMResponse(content="Great, using Flask!")

        provider = _make_mock_provider([tool_response, final_response])
        registry = create_default_registry()
        approval = ApprovalManager(ApprovalMode.AUTO)

        loop = AgentLoop(provider, registry, approval, store, session_id)

        async def ask_user_cb(
            question: str, options: list[str], allow_text: bool,
        ) -> str:
            assert question == "Which framework?"
            assert options == ["Django", "Flask"]
            return "Flask"

        result = await loop.run("help me pick", ask_user_callback=ask_user_cb)
        assert "Flask" in result

    @pytest.mark.asyncio()
    async def test_ask_user_without_callback(
        self, store: SessionStore, session_id: str,
    ) -> None:
        """ask_user without callback returns error message."""
        tool_response = LLMResponse(
            content="",
            tool_calls=[ToolCall(
                id="tc1", name="ask_user",
                arguments={"question": "How?"},
            )],
        )
        final_response = LLMResponse(content="No UI available")

        provider = _make_mock_provider([tool_response, final_response])
        registry = create_default_registry()
        approval = ApprovalManager(ApprovalMode.AUTO)

        loop = AgentLoop(provider, registry, approval, store, session_id)

        tool_statuses: list[tuple[str, str]] = []

        def on_tool_call(name: str, status: str, result: str) -> None:
            tool_statuses.append((name, status))

        await loop.run("ask something", on_tool_call=on_tool_call)
        assert any(s == "error" for _, s in tool_statuses)

    @pytest.mark.asyncio()
    async def test_ask_user_callback_returns_value(
        self, store: SessionStore, session_id: str,
    ) -> None:
        """ask_user works with an async callback returning a value."""
        tool_response = LLMResponse(
            content="",
            tool_calls=[ToolCall(
                id="tc1", name="ask_user",
                arguments={"question": "Yes or no?", "options": ["Yes", "No"]},
            )],
        )
        final_response = LLMResponse(content="OK, yes it is.")

        provider = _make_mock_provider([tool_response, final_response])
        registry = create_default_registry()
        approval = ApprovalManager(ApprovalMode.AUTO)

        loop = AgentLoop(provider, registry, approval, store, session_id)

        async def ask_cb(question: str, options: list[str], allow_text: bool) -> str:
            return "Yes"

        result = await loop.run("confirm?", ask_user_callback=ask_cb)
        assert "yes" in result.lower()

    @pytest.mark.asyncio()
    async def test_ask_user_persists_to_session(
        self, store: SessionStore, session_id: str,
    ) -> None:
        """ask_user response is stored in session history."""
        tool_response = LLMResponse(
            content="",
            tool_calls=[ToolCall(
                id="tc1", name="ask_user",
                arguments={"question": "Pick one", "options": ["A", "B"]},
            )],
        )
        final_response = LLMResponse(content="You chose A")

        provider = _make_mock_provider([tool_response, final_response])
        registry = create_default_registry()
        approval = ApprovalManager(ApprovalMode.AUTO)

        loop = AgentLoop(provider, registry, approval, store, session_id)

        async def cb(q: str, opts: list[str], at: bool) -> str:
            return "A"

        await loop.run("choose", ask_user_callback=cb)

        messages = store.get_messages(session_id)
        tool_msgs = [m for m in messages if "ask_user" in m.content]
        assert len(tool_msgs) >= 1
        assert "A" in tool_msgs[0].content

    @pytest.mark.asyncio()
    async def test_ask_user_blocked_in_autonomous_mode(
        self, store: SessionStore, session_id: str,
    ) -> None:
        """Autonomous mode should reject ask_user instead of waiting for input."""
        tool_response = LLMResponse(
            content="",
            tool_calls=[ToolCall(
                id="tc1", name="ask_user",
                arguments={"question": "Which approach should I use?"},
            )],
        )
        final_response = LLMResponse(content="Proceeding without user interaction.")

        provider = _make_mock_provider([tool_response, final_response])
        registry = create_default_registry()
        approval = ApprovalManager(ApprovalMode.AUTONOMOUS)
        tool_events: list[tuple[str, str, str]] = []

        loop = AgentLoop(provider, registry, approval, store, session_id)

        def on_tool_call(name: str, status: str, result: str) -> None:
            tool_events.append((name, status, result))

        result = await loop.run("make the best decision yourself", on_tool_call=on_tool_call)
        assert result == "Proceeding without user interaction."
        assert any(
            name == "ask_user" and status == "blocked" and "autonomous mode" in outcome.lower()
            for name, status, outcome in tool_events
        )


class TestApprovalPrompting:
    """Tests that the system prompts for permission when it needs approval."""

    @pytest.mark.asyncio()
    async def test_suggest_mode_calls_approval_callback_for_writes(
        self, store: SessionStore, session_id: str, tmp_path: Path,
    ) -> None:
        """In suggest mode, write_file triggers the approval callback."""
        tool_response = LLMResponse(
            content="",
            tool_calls=[ToolCall(
                id="tc1", name="write_file",
                arguments={"path": str(tmp_path / "out.txt"), "content": "hello"},
            )],
        )
        final_response = LLMResponse(content="Wrote the file.")

        provider = _make_mock_provider([tool_response, final_response])
        registry = create_default_registry()
        approval = ApprovalManager(ApprovalMode.SUGGEST)

        loop = AgentLoop(provider, registry, approval, store, session_id)

        callback_calls: list[tuple[str, dict[str, Any]]] = []

        async def approval_cb(tool_name: str, arguments: dict[str, Any]) -> bool:
            callback_calls.append((tool_name, arguments))
            return True

        await loop.run("write a file", approval_callback=approval_cb)

        assert len(callback_calls) == 1
        assert callback_calls[0][0] == "write_file"
        assert "content" in callback_calls[0][1]

    @pytest.mark.asyncio()
    async def test_suggest_mode_denies_when_callback_returns_false(
        self, store: SessionStore, session_id: str, tmp_path: Path,
    ) -> None:
        """When approval callback returns False, the tool call is denied."""
        tool_response = LLMResponse(
            content="",
            tool_calls=[ToolCall(
                id="tc1", name="write_file",
                arguments={"path": str(tmp_path / "out.txt"), "content": "danger"},
            )],
        )
        final_response = LLMResponse(content="User said no.")

        provider = _make_mock_provider([tool_response, final_response])
        registry = create_default_registry()
        approval = ApprovalManager(ApprovalMode.SUGGEST)

        loop = AgentLoop(provider, registry, approval, store, session_id)

        tool_statuses: list[tuple[str, str]] = []

        def on_tool_call(name: str, status: str, result: str) -> None:
            tool_statuses.append((name, status))

        async def deny_cb(tool_name: str, arguments: dict[str, Any]) -> bool:
            return False

        await loop.run(
            "write a file",
            on_tool_call=on_tool_call,
            approval_callback=deny_cb,
        )

        # Should have a "denied" status reported
        assert any(s == "denied" for _, s in tool_statuses)
        # File should NOT have been written
        assert not (tmp_path / "out.txt").exists()

    @pytest.mark.asyncio()
    async def test_no_callback_denies_tools_needing_approval(
        self, store: SessionStore, session_id: str, tmp_path: Path,
    ) -> None:
        """Without an approval callback, tools requiring approval are denied."""
        tool_response = LLMResponse(
            content="",
            tool_calls=[ToolCall(
                id="tc1", name="write_file",
                arguments={"path": str(tmp_path / "out.txt"), "content": "x"},
            )],
        )
        final_response = LLMResponse(content="denied")

        provider = _make_mock_provider([tool_response, final_response])
        registry = create_default_registry()
        approval = ApprovalManager(ApprovalMode.SUGGEST)

        loop = AgentLoop(provider, registry, approval, store, session_id)

        tool_statuses: list[tuple[str, str]] = []

        def on_tool_call(name: str, status: str, result: str) -> None:
            tool_statuses.append((name, status))

        # No approval_callback provided
        await loop.run("write a file", on_tool_call=on_tool_call)

        # Should be denied (no callback = deny for safety)
        assert any(s == "denied" for _, s in tool_statuses)
        assert not (tmp_path / "out.txt").exists()

    @pytest.mark.asyncio()
    async def test_auto_mode_skips_approval_for_file_writes(
        self, store: SessionStore, session_id: str, tmp_path: Path,
    ) -> None:
        """Auto mode does NOT prompt approval for file writes."""
        tool_response = LLMResponse(
            content="",
            tool_calls=[ToolCall(
                id="tc1", name="write_file",
                arguments={"path": str(tmp_path / "auto.txt"), "content": "auto"},
            )],
        )
        final_response = LLMResponse(content="Done")

        provider = _make_mock_provider([tool_response, final_response])
        registry = create_default_registry()
        approval = ApprovalManager(ApprovalMode.AUTO)

        loop = AgentLoop(provider, registry, approval, store, session_id)

        callback_calls: list[str] = []

        async def approval_cb(tool_name: str, arguments: dict[str, Any]) -> bool:
            callback_calls.append(tool_name)
            return True

        await loop.run("write a file", approval_callback=approval_cb)

        # In auto mode, write_file should NOT trigger the approval callback
        assert len(callback_calls) == 0
        # But the file should have been written
        assert (tmp_path / "auto.txt").exists()

    @pytest.mark.asyncio()
    async def test_mutating_tool_success_stages_and_surfaces_commit_proposal(
        self,
        store: SessionStore,
        session_id: str,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Successful FS-mutating tools should stage touched files and surface a proposal."""
        from autocode.agent.git_aware_staging import StagingResult

        tool_response = LLMResponse(
            content="",
            tool_calls=[ToolCall(
                id="tc1",
                name="write_file",
                arguments={"path": "staged.txt", "content": "staged"},
            )],
        )
        final_response = LLMResponse(content="Done")
        provider = _make_mock_provider([tool_response, final_response])
        registry = create_default_registry(project_root=str(tmp_path))
        approval = ApprovalManager(ApprovalMode.AUTO)
        calls: list[tuple[list[str], Path]] = []

        def fake_stage(files: list[str], *, project_root: Path, **kwargs: Any) -> StagingResult:
            calls.append((files, project_root))
            return StagingResult(
                staged=True,
                files=files,
                proposed_commit_message="Update staged.txt",
            )

        monkeypatch.setattr("autocode.agent.loop.stage_post_edit", fake_stage)
        loop = AgentLoop(
            provider,
            registry,
            approval,
            store,
            session_id,
            project_root=tmp_path,
        )
        tool_results: list[str] = []

        await loop.run(
            "write a file",
            on_tool_call=lambda name, status, result: tool_results.append(result)
            if status == "completed"
            else None,
        )

        assert calls == [(["staged.txt"], tmp_path)]
        assert any(
            "Proposed commit message: Update staged.txt" in result
            for result in tool_results
        )

    @pytest.mark.asyncio()
    async def test_auto_mode_hard_blocks_dangerous_write_path(
        self, store: SessionStore, session_id: str,
    ) -> None:
        """Hard-blocked write paths should not reach the tool handler."""
        registry = ToolRegistry()
        registry.register(ToolDefinition(
            name="write_file",
            description="Write content.",
            parameters={"type": "object", "properties": {}},
            handler=lambda **kwargs: (_ for _ in ()).throw(
                AssertionError("write_file handler should not run")
            ),
            requires_approval=True,
            mutates_fs=True,
        ))
        tool_response = LLMResponse(
            content="",
            tool_calls=[ToolCall(
                id="tc1",
                name="write_file",
                arguments={"path": "/etc/passwd", "content": "bad"},
            )],
        )
        final_response = LLMResponse(content="blocked")
        provider = _make_mock_provider([tool_response, final_response])
        approval = ApprovalManager(ApprovalMode.AUTO)
        loop = AgentLoop(provider, registry, approval, store, session_id)
        tool_statuses: list[tuple[str, str, str]] = []

        await loop.run(
            "write a dangerous file",
            on_tool_call=lambda name, status, result: tool_statuses.append(
                (name, status, result)
            ),
        )

        assert any(
            name == "write_file" and status == "blocked" and "/etc" in result
            for name, status, result in tool_statuses
        )

    @pytest.mark.asyncio()
    async def test_read_only_blocks_writes_entirely(
        self, store: SessionStore, session_id: str, tmp_path: Path,
    ) -> None:
        """Read-only mode blocks write tools without even asking."""
        tool_response = LLMResponse(
            content="",
            tool_calls=[ToolCall(
                id="tc1", name="write_file",
                arguments={"path": str(tmp_path / "x.txt"), "content": "x"},
            )],
        )
        final_response = LLMResponse(content="blocked")

        provider = _make_mock_provider([tool_response, final_response])
        registry = create_default_registry()
        approval = ApprovalManager(ApprovalMode.READ_ONLY)

        loop = AgentLoop(provider, registry, approval, store, session_id)

        tool_statuses: list[tuple[str, str]] = []

        def on_tool_call(name: str, status: str, result: str) -> None:
            tool_statuses.append((name, status))

        await loop.run("write a file", on_tool_call=on_tool_call)

        # Should be blocked (not even prompted)
        assert any(s == "blocked" for _, s in tool_statuses)
        assert not (tmp_path / "x.txt").exists()


class TestShellEnableOnApprove:
    """Tests that shell-disabled run_command routes through approval and enables shell."""

    @pytest.mark.asyncio()
    async def test_shell_disabled_asks_approval_then_enables(
        self, store: SessionStore, session_id: str,
    ) -> None:
        """When shell is disabled, run_command routes through approval.

        If user approves, shell gets enabled and command executes.
        """
        tool_response = LLMResponse(
            content="",
            tool_calls=[ToolCall(
                id="tc1", name="run_command",
                arguments={"command": "echo hello"},
            )],
        )
        final_response = LLMResponse(content="Command ran successfully.")

        provider = _make_mock_provider([tool_response, final_response])
        registry = create_default_registry()
        shell_config = ShellConfig(enabled=False)
        approval = ApprovalManager(ApprovalMode.SUGGEST, shell_config=shell_config)

        loop = AgentLoop(provider, registry, approval, store, session_id)

        approval_calls: list[str] = []

        async def approve_cb(tool_name: str, arguments: dict[str, Any]) -> bool:
            approval_calls.append(tool_name)
            return True

        assert approval.is_shell_disabled() is True

        result = await loop.run("run echo", approval_callback=approve_cb)

        # Approval was called for run_command
        assert "run_command" in approval_calls
        # Shell should now be enabled
        assert approval.is_shell_disabled() is False
        assert result is not None

    @pytest.mark.asyncio()
    async def test_shell_disabled_deny_keeps_shell_off(
        self, store: SessionStore, session_id: str,
    ) -> None:
        """When user denies the shell approval, shell stays disabled."""
        tool_response = LLMResponse(
            content="",
            tool_calls=[ToolCall(
                id="tc1", name="run_command",
                arguments={"command": "pwd"},
            )],
        )
        final_response = LLMResponse(content="User denied.")

        provider = _make_mock_provider([tool_response, final_response])
        registry = create_default_registry()
        shell_config = ShellConfig(enabled=False)
        approval = ApprovalManager(ApprovalMode.SUGGEST, shell_config=shell_config)

        loop = AgentLoop(provider, registry, approval, store, session_id)

        tool_statuses: list[tuple[str, str]] = []

        def on_tool_call(name: str, status: str, result: str) -> None:
            tool_statuses.append((name, status))

        async def deny_cb(tool_name: str, arguments: dict[str, Any]) -> bool:
            return False

        await loop.run("run pwd", on_tool_call=on_tool_call, approval_callback=deny_cb)

        # Should be denied
        assert any(s == "denied" for _, s in tool_statuses)
        # Shell should still be disabled
        assert approval.is_shell_disabled() is True

    @pytest.mark.asyncio()
    async def test_shell_disabled_no_callback_denies(
        self, store: SessionStore, session_id: str,
    ) -> None:
        """Without approval callback, shell-disabled run_command is denied."""
        tool_response = LLMResponse(
            content="",
            tool_calls=[ToolCall(
                id="tc1", name="run_command",
                arguments={"command": "ls"},
            )],
        )
        final_response = LLMResponse(content="No callback.")

        provider = _make_mock_provider([tool_response, final_response])
        registry = create_default_registry()
        shell_config = ShellConfig(enabled=False)
        approval = ApprovalManager(ApprovalMode.SUGGEST, shell_config=shell_config)

        loop = AgentLoop(provider, registry, approval, store, session_id)

        tool_statuses: list[tuple[str, str]] = []

        def on_tool_call(name: str, status: str, result: str) -> None:
            tool_statuses.append((name, status))

        await loop.run("run ls", on_tool_call=on_tool_call)

        assert any(s == "denied" for _, s in tool_statuses)
        assert approval.is_shell_disabled() is True


class TestInjectedContext:
    """Tests for L2 context injection into agent loop."""

    @pytest.mark.asyncio()
    async def test_injected_context_appears_in_messages(
        self, store: SessionStore, session_id: str,
    ) -> None:
        """injected_context is inserted as a system message after the main system prompt."""
        captured_messages: list[list[dict[str, Any]]] = []

        async def capturing_generate(
            messages: Any, tools: Any, **kwargs: Any,
        ) -> LLMResponse:
            captured_messages.append(list(messages))
            return LLMResponse(content="Got it.")

        mock = AsyncMock()
        mock.generate_with_tools = capturing_generate
        registry = ToolRegistry()
        approval = ApprovalManager(ApprovalMode.SUGGEST)

        loop = AgentLoop(mock, registry, approval, store, session_id)
        await loop.run("test query", injected_context="## Relevant Code\nfoo.py: def bar()")

        assert len(captured_messages) == 1
        msgs = captured_messages[0]
        # First message is system prompt, second should be injected context
        system_msgs = [m for m in msgs if m["role"] == "system"]
        assert len(system_msgs) >= 2
        assert "Relevant Code" in system_msgs[1]["content"]

    @pytest.mark.asyncio()
    async def test_no_injected_context_no_extra_message(
        self, store: SessionStore, session_id: str,
    ) -> None:
        """Without injected_context, no extra system message is added."""
        captured_messages: list[list[dict[str, Any]]] = []

        async def capturing_generate(
            messages: Any, tools: Any, **kwargs: Any,
        ) -> LLMResponse:
            captured_messages.append(list(messages))
            return LLMResponse(content="OK.")

        mock = AsyncMock()
        mock.generate_with_tools = capturing_generate
        registry = ToolRegistry()
        approval = ApprovalManager(ApprovalMode.SUGGEST)

        loop = AgentLoop(mock, registry, approval, store, session_id)
        await loop.run("test query")

        assert len(captured_messages) == 1
        msgs = captured_messages[0]
        system_msgs = [m for m in msgs if m["role"] == "system"]
        assert len(system_msgs) == 1  # Only the main system prompt


class TestTextOnlyNudge:
    """Tests for the text-only nudge feature in AUTO mode."""

    @pytest.mark.asyncio()
    async def test_auto_mode_nudges_on_text_only(
        self, store: SessionStore, session_id: str,
    ) -> None:
        """In AUTO mode, text-only responses trigger a nudge before returning."""
        call_count = 0

        async def counting_generate(
            messages: Any, tools: Any, **kwargs: Any,
        ) -> LLMResponse:
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                # First 2 calls: text-only (should be nudged)
                return LLMResponse(content=f"I think the fix is... (attempt {call_count})")
            # Third call: still text-only, but nudge limit reached
            return LLMResponse(content="Final text response")

        mock = AsyncMock()
        mock.generate_with_tools = counting_generate
        registry = ToolRegistry()
        approval = ApprovalManager(ApprovalMode.AUTO)

        loop = AgentLoop(mock, registry, approval, store, session_id)
        result = await loop.run("fix the bug")

        # Should have been called 3 times: 2 nudges + final acceptance
        assert call_count == 3
        assert "Final text response" in result

    @pytest.mark.asyncio()
    async def test_suggest_mode_does_not_nudge(
        self, store: SessionStore, session_id: str,
    ) -> None:
        """In SUGGEST mode, text-only responses return immediately (no nudge)."""
        call_count = 0

        async def counting_generate(
            messages: Any, tools: Any, **kwargs: Any,
        ) -> LLMResponse:
            nonlocal call_count
            call_count += 1
            return LLMResponse(content="Here is my answer")

        mock = AsyncMock()
        mock.generate_with_tools = counting_generate
        registry = ToolRegistry()
        approval = ApprovalManager(ApprovalMode.SUGGEST)

        loop = AgentLoop(mock, registry, approval, store, session_id)
        result = await loop.run("fix the bug")

        # Should return immediately — only 1 call
        assert call_count == 1
        assert "Here is my answer" in result

    @pytest.mark.asyncio()
    async def test_auto_mode_nudges_on_empty_no_tool_response(
        self, store: SessionStore, session_id: str,
    ) -> None:
        """AUTO mode should retry empty no-tool responses instead of returning success."""
        call_count = 0

        async def counting_generate(
            messages: Any, tools: Any, **kwargs: Any,
        ) -> LLMResponse:
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                return LLMResponse(content="")
            return LLMResponse(content="Recovered on retry")

        mock = AsyncMock()
        mock.generate_with_tools = counting_generate
        registry = ToolRegistry()
        approval = ApprovalManager(ApprovalMode.AUTO)

        loop = AgentLoop(mock, registry, approval, store, session_id)
        result = await loop.run("fix the bug")

        assert call_count == 3
        assert result == "Recovered on retry"

    @pytest.mark.asyncio()
    async def test_empty_no_tool_response_returns_diagnostic(
        self, store: SessionStore, session_id: str,
    ) -> None:
        """Empty no-tool responses should return a diagnostic instead of empty text."""
        provider = _make_mock_provider([LLMResponse(content="")])
        registry = ToolRegistry()
        approval = ApprovalManager(ApprovalMode.SUGGEST)

        loop = AgentLoop(provider, registry, approval, store, session_id)
        result = await loop.run("fix the bug")

        assert "empty response" in result.lower()
        assert "tool calls" in result.lower()

    @pytest.mark.asyncio()
    async def test_multi_step_requests_require_task_creation_before_other_tools(
        self, store: SessionStore, session_id: str, tmp_path: Path,
    ) -> None:
        """Planning middleware should force task creation before other tools."""
        test_file = tmp_path / "sample.py"
        test_file.write_text("print('hello')\n", encoding="utf-8")
        responses = [
            LLMResponse(
                content="",
                tool_calls=[ToolCall(
                    id="tc1",
                    name="read_file",
                    arguments={"path": str(test_file)},
                )],
            ),
            LLMResponse(
                content="",
                tool_calls=[ToolCall(
                    id="tc2",
                    name="create_task",
                    arguments={"title": "Inspect sample.py", "description": "Read before editing"},
                )],
            ),
            LLMResponse(content="Task board established."),
        ]
        seen_tool_names: list[set[str]] = []
        call_count = 0

        async def generate_with_tools(messages: Any, tools: Any, **kwargs: Any) -> LLMResponse:
            nonlocal call_count
            call_count += 1
            seen_tool_names.append({tool["function"]["name"] for tool in tools})
            return responses[min(call_count - 1, len(responses) - 1)]

        provider = AsyncMock()
        provider.generate_with_tools = generate_with_tools
        registry = create_default_registry(project_root=str(tmp_path))
        task_store = TaskStore(store.get_connection(), session_id)
        register_task_tools(registry, task_store)
        approval = ApprovalManager(ApprovalMode.AUTO)

        loop = AgentLoop(
            provider,
            registry,
            approval,
            store,
            session_id,
            task_store=task_store,
            middleware=create_default_middleware(),
        )

        result = await loop.run("Rename the module and update tests across multiple files")

        assert result == "Task board established."
        assert "create_task" in seen_tool_names[0]
        assert "list_tasks" in seen_tool_names[0]
        tasks = task_store.list_tasks()
        assert len(tasks) == 1
        assert tasks[0].title == "Inspect sample.py"

        tool_rows = store.get_connection().execute(
            "SELECT tool_name, status, result FROM tool_calls ORDER BY id ASC",
        ).fetchall()
        assert tool_rows[0]["tool_name"] == "read_file"
        assert tool_rows[0]["status"] == "blocked"
        assert "planning enforcement" in tool_rows[0]["result"].lower()

    @pytest.mark.asyncio()
    async def test_mutations_require_verification_before_completion(
        self, store: SessionStore, session_id: str, tmp_path: Path,
    ) -> None:
        """after_model middleware should retry until a verification tool runs."""
        target = tmp_path / "app.py"
        target.write_text("value = 1\n", encoding="utf-8")
        seen_messages: list[list[dict[str, Any]]] = []
        call_count = 0

        async def generate_with_tools(
            messages: Any, tools: Any, **kwargs: Any,
        ) -> LLMResponse:
            nonlocal call_count
            call_count += 1
            seen_messages.append([dict(m) for m in messages])
            if call_count == 1:
                return LLMResponse(
                    content="",
                    tool_calls=[ToolCall(
                        id="tc1",
                        name="edit_file",
                        arguments={
                            "path": str(target),
                            "old_string": "value = 1",
                            "new_string": "value = 2",
                        },
                    )],
                )
            if call_count == 2:
                return LLMResponse(content="Done, the file is fixed.")
            if call_count == 3:
                return LLMResponse(
                    content="",
                    tool_calls=[ToolCall(
                        id="tc2",
                        name="read_file",
                        arguments={"path": str(target)},
                    )],
                )
            return LLMResponse(content="Verified and complete.")

        provider = AsyncMock()
        provider.generate_with_tools = generate_with_tools
        registry = create_default_registry(project_root=str(tmp_path))
        approval = ApprovalManager(ApprovalMode.SUGGEST)

        loop = AgentLoop(
            provider,
            registry,
            approval,
            store,
            session_id,
            middleware=create_default_middleware(),
        )
        result = await loop.run(
            "Fix app.py and make sure it really works",
            approval_callback=AsyncMock(return_value=True),
        )

        assert result == "Verified and complete."
        assert call_count == 4
        assert any(
            msg.get("role") == "user" and "verify your changes" in msg.get("content", "").lower()
            for msg in seen_messages[2]
        )

    @pytest.mark.asyncio()
    async def test_first_turn_includes_environment_bootstrap_snapshot(
        self,
        store: SessionStore,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Iteration-zero bootstrap should stay cheap on the first user turn."""
        session_id = store.create_session(
            title="Env bootstrap",
            model="m",
            provider="mock",
            project_dir=str(tmp_path),
        )
        (tmp_path / "README.md").write_text("hello\n", encoding="utf-8")
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "app.py").write_text(
            "class App:\n    def run(self):\n        return 'ok'\n",
            encoding="utf-8",
        )

        captured_messages: list[list[dict[str, Any]]] = []

        async def fake_generate(messages: Any, tools: Any, **kwargs: Any) -> LLMResponse:
            captured_messages.append([dict(message) for message in messages])
            return LLMResponse(content="done")

        warm_index = Mock(side_effect=AssertionError("warm_code_index should stay deferred"))
        repo_map_generate = Mock(side_effect=AssertionError("repo map should stay deferred"))
        monkeypatch.setattr("autocode.agent.tools.warm_code_index", warm_index)
        monkeypatch.setattr(
            "autocode.layer2.repomap.RepoMapGenerator.generate",
            repo_map_generate,
        )

        provider = AsyncMock()
        provider.generate_with_tools = fake_generate
        registry = create_default_registry(project_root=str(tmp_path))
        approval = ApprovalManager(ApprovalMode.SUGGEST)
        loop = AgentLoop(
            provider,
            registry,
            approval,
            store,
            session_id,
            middleware=create_default_middleware(),
        )

        result = await loop.run("summarize the repo")

        assert result == "done"
        bootstrap_messages = [
            msg for msg in captured_messages[0]
            if msg.get("role") == "system" and "Workspace Bootstrap" in msg.get("content", "")
        ]
        assert bootstrap_messages
        assert warm_index.call_count == 0
        assert repo_map_generate.call_count == 0
        assert "Project root" in bootstrap_messages[0]["content"]
        assert "Retrieval index" in bootstrap_messages[0]["content"]
        assert "deferred" in bootstrap_messages[0]["content"].lower()
        assert "Available tools" in bootstrap_messages[0]["content"]

    @pytest.mark.asyncio()
    async def test_bootstrap_snapshot_includes_active_working_set(
        self, store: SessionStore, tmp_path: Path,
    ) -> None:
        """Bootstrap should surface the currently hot files when known."""
        from autocode.agent.tools import clear_active_working_set, record_active_file

        session_id = store.create_session(
            title="Env bootstrap with working set",
            model="m",
            provider="mock",
            project_dir=str(tmp_path),
        )
        tracked = tmp_path / "src" / "tracked.py"
        tracked.parent.mkdir()
        tracked.write_text("def tracked():\n    return 1\n", encoding="utf-8")
        clear_active_working_set()
        record_active_file(tracked, project_root=str(tmp_path), weight=3)

        captured_messages: list[list[dict[str, Any]]] = []

        async def fake_generate(messages: Any, tools: Any, **kwargs: Any) -> LLMResponse:
            captured_messages.append([dict(message) for message in messages])
            return LLMResponse(content="done")

        provider = AsyncMock()
        provider.generate_with_tools = fake_generate
        registry = create_default_registry(project_root=str(tmp_path))
        approval = ApprovalManager(ApprovalMode.SUGGEST)
        loop = AgentLoop(
            provider,
            registry,
            approval,
            store,
            session_id,
            middleware=create_default_middleware(),
        )

        result = await loop.run("summarize the repo")

        assert result == "done"
        bootstrap_message = next(
            msg for msg in captured_messages[0]
            if msg.get("role") == "system" and "Workspace Bootstrap" in msg.get("content", "")
        )
        assert "Active working set" in bootstrap_message["content"]
        assert "src/tracked.py" in bootstrap_message["content"]

    @pytest.mark.asyncio()
    async def test_bootstrap_snapshot_includes_cached_l1_symbol_preview(
        self, store: SessionStore, tmp_path: Path,
    ) -> None:
        """Bootstrap should include cached Layer 1 symbols for hot files."""
        from autocode.agent.tools import clear_active_working_set, record_active_file
        from autocode.layer1.queries import DeterministicQueryHandler

        session_id = store.create_session(
            title="Env bootstrap with symbols",
            model="m",
            provider="mock",
            project_dir=str(tmp_path),
        )
        tracked = tmp_path / "src" / "tracked.py"
        tracked.parent.mkdir()
        tracked.write_text(
            "class Worker:\n"
            "    def run(self):\n"
            "        return 1\n\n"
            "def build_worker():\n"
            "    return Worker()\n",
            encoding="utf-8",
        )
        clear_active_working_set()
        query_handler = DeterministicQueryHandler(project_root=tmp_path)
        response = query_handler.handle("list symbols in src/tracked.py")
        assert response.success
        record_active_file(tracked, project_root=str(tmp_path), weight=3)

        captured_messages: list[list[dict[str, Any]]] = []

        async def fake_generate(messages: Any, tools: Any, **kwargs: Any) -> LLMResponse:
            captured_messages.append([dict(message) for message in messages])
            return LLMResponse(content="done")

        provider = AsyncMock()
        provider.generate_with_tools = fake_generate
        registry = create_default_registry(project_root=str(tmp_path))
        approval = ApprovalManager(ApprovalMode.SUGGEST)
        loop = AgentLoop(
            provider,
            registry,
            approval,
            store,
            session_id,
            middleware=create_default_middleware(),
        )

        result = await loop.run("summarize the active work")

        assert result == "done"
        bootstrap_message = next(
            msg for msg in captured_messages[0]
            if msg.get("role") == "system" and "Workspace Bootstrap" in msg.get("content", "")
        )
        assert "Active symbol preview" in bootstrap_message["content"]
        assert "src/tracked.py" in bootstrap_message["content"]
        assert "class Worker" in bootstrap_message["content"]
        assert "function build_worker" in bootstrap_message["content"]

    @pytest.mark.asyncio()
    async def test_bootstrap_symbol_preview_skips_slow_builder(
        self,
        store: SessionStore,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Slow preview generation should not leak into the bootstrap snapshot."""
        import time

        from autocode.agent.tools import clear_active_working_set, record_active_file

        session_id = store.create_session(
            title="Env bootstrap slow symbols",
            model="m",
            provider="mock",
            project_dir=str(tmp_path),
        )
        tracked = tmp_path / "src" / "tracked.py"
        tracked.parent.mkdir()
        tracked.write_text("def tracked():\n    return 1\n", encoding="utf-8")
        clear_active_working_set()
        record_active_file(tracked, project_root=str(tmp_path), weight=3)

        def slow_preview(**kwargs: Any) -> str:
            time.sleep(0.2)
            return "- Active symbol preview:\n  - src/tracked.py: function tracked:L1"

        monkeypatch.setattr("autocode.agent.loop.build_active_symbol_preview", slow_preview)
        captured_messages: list[list[dict[str, Any]]] = []

        async def fake_generate(messages: Any, tools: Any, **kwargs: Any) -> LLMResponse:
            captured_messages.append([dict(message) for message in messages])
            return LLMResponse(content="done")

        provider = AsyncMock()
        provider.generate_with_tools = fake_generate
        registry = create_default_registry(project_root=str(tmp_path))
        approval = ApprovalManager(ApprovalMode.SUGGEST)
        loop = AgentLoop(
            provider,
            registry,
            approval,
            store,
            session_id,
            middleware=create_default_middleware(),
        )

        result = await loop.run("summarize the active work")

        assert result == "done"
        bootstrap_message = next(
            msg for msg in captured_messages[0]
            if msg.get("role") == "system" and "Workspace Bootstrap" in msg.get("content", "")
        )
        assert "Active working set" in bootstrap_message["content"]
        assert "Active symbol preview" not in bootstrap_message["content"]

    @pytest.mark.asyncio()
    async def test_after_tool_middleware_result_is_persisted(
        self, store: SessionStore, session_id: str, tmp_path: Path,
    ) -> None:
        """after_tool middleware should modify the stored/displayed tool result."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("original")

        provider = _make_mock_provider([
            LLMResponse(
                content="",
                tool_calls=[ToolCall(
                    id="tc1",
                    name="read_file",
                    arguments={"path": str(test_file)},
                )],
            ),
            LLMResponse(content="done"),
        ])
        middleware = MiddlewareStack()
        middleware.add(
            "after_tool",
            lambda ctx: setattr(ctx, "modified_result", f"sanitized: {ctx.tool_name}"),
        )
        registry = create_default_registry()
        approval = ApprovalManager(ApprovalMode.AUTO)
        tool_events: list[tuple[str, str, str]] = []

        def on_tool_call(name: str, status: str, result: str) -> None:
            tool_events.append((name, status, result))

        loop = AgentLoop(
            provider,
            registry,
            approval,
            store,
            session_id,
            middleware=middleware,
        )
        await loop.run("read the file", on_tool_call=on_tool_call)

        conn = store.get_connection()
        row = conn.execute("SELECT result FROM tool_calls ORDER BY id DESC LIMIT 1").fetchone()
        assert row is not None
        assert row["result"] == "sanitized: read_file"
        assert ("read_file", "completed", "sanitized: read_file") in tool_events

        tool_messages = [m.content for m in store.get_messages(session_id) if m.role == "tool"]
        assert any("sanitized: read_file" in msg for msg in tool_messages)


class TestPhase7RuntimeWiring:
    """Tests for the Phase 7 runtime parity fixes."""

    @pytest.mark.asyncio()
    async def test_middleware_hooks_cover_compaction_and_after_model(
        self, store: SessionStore, session_id: str,
    ) -> None:
        """Compaction and after-model hooks should run in the live loop."""
        for i in range(8):
            store.add_message(session_id, "assistant", f"prior message {i} " * 40)

        hook_events: list[str] = []
        middleware = MiddlewareStack()
        middleware.add("before_model", lambda ctx: hook_events.append("before_model"))
        middleware.add("after_model", lambda ctx: hook_events.append("after_model"))
        middleware.add("before_compaction", lambda ctx: hook_events.append("before_compaction"))
        middleware.add("after_compaction", lambda ctx: hook_events.append("after_compaction"))

        provider = AsyncMock()

        async def fake_generate_with_tools(messages: Any, tools: Any, **kwargs: Any) -> LLMResponse:
            return LLMResponse(content="done")

        async def fake_generate(messages: Any, **kwargs: Any):
            yield "summary"

        provider.generate_with_tools = fake_generate_with_tools
        provider.generate = fake_generate
        registry = ToolRegistry()
        approval = ApprovalManager(ApprovalMode.SUGGEST)
        context_engine = ContextEngine(
            provider=provider,
            session_store=store,
            context_length=256,
            compaction_threshold=0.2,
        )

        loop = AgentLoop(
            provider,
            registry,
            approval,
            store,
            session_id,
            context_engine=context_engine,
            middleware=middleware,
        )

        result = await loop.run("finish this")

        assert result == "done"
        assert "before_compaction" in hook_events
        assert "after_compaction" in hook_events
        assert "before_model" in hook_events
        assert "after_model" in hook_events

    @pytest.mark.asyncio()
    async def test_spawn_subagent_respects_delegation_policy(
        self, store: SessionStore, session_id: str,
    ) -> None:
        """The live loop should block subagent spawns when delegation says no."""
        provider = _make_mock_provider([
            LLMResponse(
                content="",
                tool_calls=[ToolCall(
                    id="tc1",
                    name="spawn_subagent",
                    arguments={"subagent_type": "explore", "task": "inspect repo"},
                )],
            ),
            LLMResponse(content="blocked"),
        ])
        approval = ApprovalManager(ApprovalMode.AUTO)
        registry = create_default_registry()
        scheduler = LLMScheduler()
        manager = SubagentManager(
            provider=AsyncMock(),
            tool_registry=registry,
            scheduler=scheduler,
            max_concurrent=3,
        )
        register_subagent_tools(registry, manager)
        policy = DelegationPolicy(max_total_agents=0)

        loop = AgentLoop(
            provider,
            registry,
            approval,
            store,
            session_id,
            subagent_manager=manager,
            delegation_policy=policy,
        )

        tool_statuses: list[tuple[str, str, str]] = []

        def on_tool_call(name: str, status: str, result: str) -> None:
            tool_statuses.append((name, status, result))

        try:
            result = await loop.run("delegate this", on_tool_call=on_tool_call)

            assert result == "blocked"
            assert any(
                name == "spawn_subagent" and status == "blocked" and "Delegation policy" in output
                for name, status, output in tool_statuses
            )
        finally:
            await scheduler.shutdown()


class TestPromptSplitting:
    """Tests for static/dynamic system prompt splitting."""

    def test_build_static_prefix_returns_system_prompt(self) -> None:
        """build_static_prefix() returns the SYSTEM_PROMPT constant."""
        result = build_static_prefix()
        assert result == SYSTEM_PROMPT

    def test_build_static_prefix_is_stable(self) -> None:
        """build_static_prefix() returns the same string on repeated calls."""
        a = build_static_prefix()
        b = build_static_prefix()
        assert a == b

    def test_static_prompt_requires_in_progress_before_first_action(self) -> None:
        """Task guidance requires an observable in-progress lifecycle step."""
        prompt = build_static_prefix()

        assert "pending -> in_progress -> completed" in prompt
        assert "before the first concrete action" in prompt

    def test_build_dynamic_suffix_includes_approval_mode(self) -> None:
        """Dynamic suffix includes the approval mode."""
        result = build_dynamic_suffix(approval_mode="auto")
        assert "Approval mode: auto" in result

    def test_build_dynamic_suffix_includes_shell_status(self) -> None:
        """Dynamic suffix includes shell enabled/disabled status."""
        enabled = build_dynamic_suffix(shell_enabled=True)
        assert "ENABLED" in enabled

        disabled = build_dynamic_suffix(shell_enabled=False)
        assert "DISABLED" in disabled

    def test_build_dynamic_suffix_includes_memory(self) -> None:
        """Dynamic suffix includes memory content when provided."""
        result = build_dynamic_suffix(memory_content="remember this")
        assert "remember this" in result

    def test_build_dynamic_suffix_includes_plan_mode(self) -> None:
        """Dynamic suffix includes plan mode flag when active."""
        result = build_dynamic_suffix(plan_mode=True)
        assert "PLANNING" in result

    def test_build_dynamic_suffix_includes_research_mode(self) -> None:
        """Dynamic suffix includes research-mode handoff guidance."""
        result = build_dynamic_suffix(research_mode=True)
        assert "RESEARCH" in result
        assert "candidate files and symbols" in result
        assert "/research off" in result

    def test_build_dynamic_suffix_empty_when_minimal(self) -> None:
        """Dynamic suffix with defaults still has environment section."""
        result = build_dynamic_suffix()
        assert "Current Environment" in result

    def test_build_system_prompt_backward_compatible(self) -> None:
        """build_system_prompt() returns static + dynamic concatenated."""
        full = build_system_prompt(
            memory_content="test memory",
            shell_enabled=True,
            approval_mode="auto",
        )
        static = build_static_prefix()
        dynamic = build_dynamic_suffix(
            memory_content="test memory",
            shell_enabled=True,
            approval_mode="auto",
        )
        assert full == static + dynamic

    def test_build_dynamic_suffix_includes_all_sections(self) -> None:
        """Dynamic suffix includes all optional sections when provided."""
        result = build_dynamic_suffix(
            memory_content="mem",
            context="ctx",
            task_summary="tasks",
            subagent_status="agents",
            memory_context="patterns",
        )
        assert "mem" in result
        assert "ctx" in result
        assert "tasks" in result
        assert "agents" in result
        assert "patterns" in result


class TestAgentLoopCaching:
    """Tests for caching optimizations in AgentLoop."""

    @pytest.mark.asyncio()
    async def test_static_prefix_cached_across_iterations(
        self, store: SessionStore, session_id: str,
    ) -> None:
        """_static_prefix is computed once and reused (same object identity)."""
        # Two iterations: first returns tool call, second returns text
        tool_response = LLMResponse(
            content="",
            tool_calls=[ToolCall(id="tc1", name="unknown_tool", arguments={})],
        )
        final_response = LLMResponse(content="done")
        provider = _make_mock_provider([tool_response, final_response])
        registry = ToolRegistry()
        approval = ApprovalManager(ApprovalMode.SUGGEST)

        loop = AgentLoop(provider, registry, approval, store, session_id)

        # Before run, _static_prefix should be None
        assert loop._static_prefix is None

        await loop.run("test caching")

        # After run, _static_prefix should be set
        assert loop._static_prefix is not None
        first_ref = loop._static_prefix

        # Run again -- should reuse the same cached string object
        await loop.run("test caching again")
        assert loop._static_prefix is first_ref

    @pytest.mark.asyncio()
    async def test_tool_schemas_cached_across_iterations(
        self, store: SessionStore, session_id: str,
    ) -> None:
        """Tool schemas are computed once and reused across iterations."""
        captured_tools: list[list[dict[str, Any]]] = []

        async def capturing_generate(
            messages: Any, tools: Any, **kwargs: Any,
        ) -> LLMResponse:
            captured_tools.append(tools)
            return LLMResponse(content="done")

        mock = AsyncMock()
        mock.generate_with_tools = capturing_generate
        registry = create_default_registry()
        approval = ApprovalManager(ApprovalMode.SUGGEST)

        loop = AgentLoop(mock, registry, approval, store, session_id)

        # Before run, _cached_tool_schemas should be None
        assert loop._cached_tool_schemas is None

        await loop.run("first")
        # After run, should be cached
        assert loop._cached_tool_schemas is not None
        first_ref = loop._cached_tool_schemas

        await loop.run("second")
        # Same object should be reused
        assert loop._cached_tool_schemas is first_ref

    @pytest.mark.asyncio()
    async def test_cached_tool_schemas_match_fresh(
        self, store: SessionStore, session_id: str,
    ) -> None:
        """Cached tool schemas have the same content as freshly computed ones."""
        provider = _make_mock_provider([LLMResponse(content="ok")])
        registry = create_default_registry()
        approval = ApprovalManager(ApprovalMode.SUGGEST)

        loop = AgentLoop(provider, registry, approval, store, session_id)
        await loop.run("test")

        fresh = registry.get_core_schemas_openai_format()
        assert loop._cached_tool_schemas == fresh
