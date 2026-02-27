"""Tests for the agent loop."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pytest

from autocode.agent.approval import ApprovalManager, ApprovalMode
from autocode.agent.loop import AgentLoop
from autocode.agent.tools import ToolRegistry, create_default_registry
from autocode.config import ShellConfig
from autocode.layer4.llm import LLMResponse, ToolCall
from autocode.session.store import SessionStore


@pytest.fixture()
def store(tmp_path: Path) -> SessionStore:
    s = SessionStore(tmp_path / "test.db")
    yield s
    s.close()


@pytest.fixture()
def session_id(store: SessionStore) -> str:
    return store.create_session(title="Test", model="m", provider="mock")


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
