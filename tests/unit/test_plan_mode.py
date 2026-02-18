"""Tests for plan mode — Sprint 4B."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from autocode.agent.approval import ApprovalManager, ApprovalMode
from autocode.agent.loop import AgentLoop, AgentMode
from autocode.agent.prompts import build_system_prompt
from autocode.agent.tools import ToolDefinition, ToolRegistry
from autocode.config import ShellConfig
from autocode.layer4.llm import ToolCall


def _make_registry() -> ToolRegistry:
    reg = ToolRegistry()
    reg.register(ToolDefinition(
        name="read_file",
        description="Read a file",
        parameters={
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
        handler=lambda **kw: "file contents",
    ))
    reg.register(ToolDefinition(
        name="write_file",
        description="Write a file",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
        },
        handler=lambda **kw: f"Written to {kw.get('path', 'unknown')}",
        requires_approval=True,
        mutates_fs=True,
    ))
    reg.register(ToolDefinition(
        name="run_command",
        description="Run command",
        parameters={
            "type": "object",
            "properties": {"command": {"type": "string"}},
            "required": ["command"],
        },
        handler=lambda **kw: "ok",
        requires_approval=True,
        executes_shell=True,
    ))
    return reg


def _make_agent_loop(mode: AgentMode = AgentMode.NORMAL) -> AgentLoop:
    provider = AsyncMock()
    session_store = MagicMock()
    session_store.get_messages.return_value = []
    session_store.add_message.return_value = 1
    session_store.add_tool_call.return_value = 1

    approval = ApprovalManager(
        mode=ApprovalMode.AUTO,
        shell_config=ShellConfig(enabled=True),
    )

    loop = AgentLoop(
        provider=provider,
        tool_registry=_make_registry(),
        approval_manager=approval,
        session_store=session_store,
        session_id="test-session",
    )
    loop.set_mode(mode)
    return loop


def test_agent_mode_default_normal():
    """Agent mode defaults to NORMAL."""
    loop = _make_agent_loop()
    assert loop.get_mode() == AgentMode.NORMAL


def test_agent_mode_set_planning():
    """set_mode changes mode to PLANNING."""
    loop = _make_agent_loop()
    loop.set_mode(AgentMode.PLANNING)
    assert loop.get_mode() == AgentMode.PLANNING


@pytest.mark.asyncio
async def test_plan_mode_blocks_write_file():
    """Plan mode blocks tools with mutates_fs=True."""
    loop = _make_agent_loop(AgentMode.PLANNING)

    # Simulate a write_file tool call
    tc = ToolCall(id="tc1", name="write_file", arguments={"path": "test.py", "content": "x"})
    result = await loop._execute_tool_call(tc, msg_id=1)

    assert "Blocked in plan mode" in result
    assert "write_file" in result


@pytest.mark.asyncio
async def test_plan_mode_blocks_run_command():
    """Plan mode blocks tools with executes_shell=True."""
    loop = _make_agent_loop(AgentMode.PLANNING)

    tc = ToolCall(id="tc1", name="run_command", arguments={"command": "ls"})
    result = await loop._execute_tool_call(tc, msg_id=1)

    assert "Blocked in plan mode" in result
    assert "run_command" in result


@pytest.mark.asyncio
async def test_plan_mode_allows_read_file():
    """Plan mode allows read-only tools."""
    loop = _make_agent_loop(AgentMode.PLANNING)

    tc = ToolCall(id="tc1", name="read_file", arguments={"path": "test.py"})
    result = await loop._execute_tool_call(tc, msg_id=1)

    assert "file contents" in result
    assert "Blocked" not in result


def test_system_prompt_includes_plan_mode():
    """System prompt includes plan mode indicator when active."""
    prompt = build_system_prompt(plan_mode=True)
    assert "PLANNING" in prompt
    assert "/plan approve" in prompt

    prompt_normal = build_system_prompt(plan_mode=False)
    assert "PLANNING" not in prompt_normal
