"""Tests for the approval manager."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pytest

from autocode.agent.approval import ApprovalManager, ApprovalMode
from autocode.agent.tools import ToolDefinition, create_default_registry
from autocode.config import ShellConfig


def _make_tool(name: str, requires_approval: bool = False) -> ToolDefinition:
    return ToolDefinition(
        name=name,
        description=f"Test tool {name}",
        parameters={"type": "object", "properties": {}},
        handler=lambda: "ok",
        requires_approval=requires_approval,
    )


class TestApprovalManager:
    def test_read_only_blocks_writes(self) -> None:
        """Read-only mode blocks write operations."""
        mgr = ApprovalManager(ApprovalMode.READ_ONLY)
        assert mgr.is_write_blocked("write_file") is True
        assert mgr.is_write_blocked("run_command") is True
        assert mgr.is_write_blocked("read_file") is False

    def test_suggest_requires_approval_for_writes(self) -> None:
        """Suggest mode requires approval for tools with requires_approval=True."""
        mgr = ApprovalManager(ApprovalMode.SUGGEST)
        write_tool = _make_tool("write_file", requires_approval=True)
        read_tool = _make_tool("read_file", requires_approval=False)

        assert mgr.needs_approval(write_tool) is True
        assert mgr.needs_approval(read_tool) is False

    def test_auto_allows_file_writes(self) -> None:
        """Auto mode auto-approves file writes."""
        mgr = ApprovalManager(ApprovalMode.AUTO)
        write_tool = _make_tool("write_file", requires_approval=True)

        # In auto mode, only run_command needs approval
        assert mgr.needs_approval(write_tool) is False

    def test_auto_still_prompts_for_shell(self) -> None:
        """Auto mode still requires approval for run_command."""
        mgr = ApprovalManager(ApprovalMode.AUTO)
        shell_tool = _make_tool("run_command", requires_approval=True)

        assert mgr.needs_approval(shell_tool) is True

    def test_autonomous_never_prompts(self) -> None:
        """Autonomous mode should avoid interactive approval prompts."""
        mgr = ApprovalManager(ApprovalMode.AUTONOMOUS)
        write_tool = _make_tool("write_file", requires_approval=True)
        shell_tool = _make_tool("run_command", requires_approval=True)

        assert mgr.needs_approval(write_tool) is False
        assert mgr.needs_approval(shell_tool) is False

    def test_shell_disabled_not_hard_blocked(self) -> None:
        """When shell is disabled, run_command is NOT hard-blocked (routes to approval)."""
        shell_config = ShellConfig(enabled=False)
        mgr = ApprovalManager(ApprovalMode.AUTO, shell_config=shell_config)

        blocked, _reason = mgr.is_blocked("run_command", {"command": "ls"})
        assert blocked is False
        assert mgr.is_shell_disabled() is True

    def test_blocked_commands_always_rejected(self) -> None:
        """Dangerous commands are always blocked regardless of mode."""
        shell_config = ShellConfig(enabled=True)
        mgr = ApprovalManager(ApprovalMode.AUTO, shell_config=shell_config)

        blocked, reason = mgr.is_blocked("run_command", {"command": "rm -rf /"})
        assert blocked is True
        assert "dangerous" in reason.lower() or "blocked" in reason.lower()

        # sudo should also be blocked
        blocked2, reason2 = mgr.is_blocked("run_command", {"command": "sudo rm something"})
        assert blocked2 is True

    def test_shell_enabled_allows_run_command(self) -> None:
        """When shell is enabled, run_command is not blocked."""
        shell_config = ShellConfig(enabled=True)
        mgr = ApprovalManager(ApprovalMode.AUTO, shell_config=shell_config)

        blocked, reason = mgr.is_blocked("run_command", {"command": "pytest tests/"})
        assert blocked is False

    def test_mode_can_be_changed_at_runtime(self) -> None:
        """ApprovalManager mode can be changed dynamically."""
        mgr = ApprovalManager(ApprovalMode.SUGGEST)
        write_tool = _make_tool("write_file", requires_approval=True)

        # In suggest mode: needs approval
        assert mgr.needs_approval(write_tool) is True

        # Switch to auto mode
        mgr.mode = ApprovalMode.AUTO
        assert mgr.needs_approval(write_tool) is False

    def test_shell_config_can_be_toggled(self) -> None:
        """Shell config enabled flag can be toggled at runtime."""
        shell_config = ShellConfig(enabled=False)
        mgr = ApprovalManager(ApprovalMode.AUTO, shell_config=shell_config)

        assert mgr.is_shell_disabled() is True

        # Toggle shell on via enable_shell()
        mgr.enable_shell()
        assert mgr.is_shell_disabled() is False

    def test_dangerous_command_blocked_even_with_shell_disabled(self) -> None:
        """Dangerous commands are hard-blocked regardless of shell state."""
        shell_config = ShellConfig(enabled=False)
        mgr = ApprovalManager(ApprovalMode.AUTO, shell_config=shell_config)

        blocked, reason = mgr.is_blocked("run_command", {"command": "rm -rf /"})
        assert blocked is True
        assert "dangerous" in reason.lower() or "blocked" in reason.lower()


class TestAsyncApprovalCallback:
    """Tests that async approval callbacks work in the agent loop."""

    @pytest.fixture()
    def store(self, tmp_path: Path) -> Any:
        from autocode.session.store import SessionStore

        s = SessionStore(tmp_path / "test.db")
        yield s
        s.close()

    @pytest.fixture()
    def session_id(self, store: Any) -> str:
        return store.create_session(title="Test", model="m", provider="mock")

    @pytest.mark.asyncio()
    async def test_async_approval_callback_works(
        self, store: Any, session_id: str, tmp_path: Path,
    ) -> None:
        """Agent loop correctly awaits an async approval callback."""
        from autocode.agent.loop import AgentLoop
        from autocode.layer4.llm import LLMResponse, ToolCall

        tool_response = LLMResponse(
            content="",
            tool_calls=[ToolCall(
                id="tc1", name="write_file",
                arguments={"path": str(tmp_path / "async_test.txt"), "content": "async"},
            )],
        )
        final_response = LLMResponse(content="Done")

        mock = AsyncMock()
        call_count = 0

        async def fake_gen(messages: Any, tools: Any, **kwargs: Any) -> LLMResponse:
            nonlocal call_count
            idx = min(call_count, 1)
            call_count += 1
            return [tool_response, final_response][idx]

        mock.generate_with_tools = fake_gen

        registry = create_default_registry()
        approval = ApprovalManager(ApprovalMode.SUGGEST)

        loop = AgentLoop(mock, registry, approval, store, session_id)

        # Async callback
        async def async_cb(tool_name: str, arguments: dict[str, Any]) -> bool:
            return True

        await loop.run("write a file", approval_callback=async_cb)
        assert (tmp_path / "async_test.txt").exists()

    @pytest.mark.asyncio()
    async def test_async_approval_deny_works(
        self, store: Any, session_id: str, tmp_path: Path,
    ) -> None:
        """Agent loop correctly handles async deny."""
        from autocode.agent.loop import AgentLoop
        from autocode.layer4.llm import LLMResponse, ToolCall

        tool_response = LLMResponse(
            content="",
            tool_calls=[ToolCall(
                id="tc1", name="write_file",
                arguments={"path": str(tmp_path / "denied.txt"), "content": "no"},
            )],
        )
        final_response = LLMResponse(content="Denied")

        mock = AsyncMock()
        call_count = 0

        async def fake_gen(messages: Any, tools: Any, **kwargs: Any) -> LLMResponse:
            nonlocal call_count
            idx = min(call_count, 1)
            call_count += 1
            return [tool_response, final_response][idx]

        mock.generate_with_tools = fake_gen

        registry = create_default_registry()
        approval = ApprovalManager(ApprovalMode.SUGGEST)

        loop = AgentLoop(mock, registry, approval, store, session_id)

        async def async_deny(tool_name: str, arguments: dict[str, Any]) -> bool:
            return False

        await loop.run("write a file", approval_callback=async_deny)
        assert not (tmp_path / "denied.txt").exists()

    @pytest.mark.asyncio()
    async def test_autonomous_mode_blocks_shell_when_disabled(
        self, store: Any, session_id: str,
    ) -> None:
        """Autonomous mode should fail closed instead of prompting to enable shell."""
        from autocode.agent.loop import AgentLoop
        from autocode.layer4.llm import LLMResponse, ToolCall

        tool_response = LLMResponse(
            content="",
            tool_calls=[ToolCall(
                id="tc1", name="run_command", arguments={"command": "pytest -q"},
            )],
        )
        final_response = LLMResponse(content="could not run shell")

        mock = AsyncMock()
        call_count = 0

        async def fake_gen(messages: Any, tools: Any, **kwargs: Any) -> LLMResponse:
            nonlocal call_count
            idx = min(call_count, 1)
            call_count += 1
            return [tool_response, final_response][idx]

        mock.generate_with_tools = fake_gen

        registry = create_default_registry()
        approval = ApprovalManager(
            ApprovalMode.AUTONOMOUS,
            shell_config=ShellConfig(enabled=False),
        )

        loop = AgentLoop(mock, registry, approval, store, session_id)
        tool_events: list[tuple[str, str, str]] = []

        def on_tool_call(name: str, status: str, result: str) -> None:
            tool_events.append((name, status, result))

        result = await loop.run("run the test suite", on_tool_call=on_tool_call)
        assert "could not run shell" in result
        assert ("run_command", "blocked", tool_events[0][2]) == tool_events[0]
        assert "autonomous mode" in tool_events[0][2].lower()
