"""Tests for subagent tool definitions and handlers — Sprint 4B."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest

from autocode.agent.subagent import (
    LLMScheduler,
    SubagentManager,
)
from autocode.agent.subagent_tools import register_subagent_tools
from autocode.agent.tools import ToolDefinition, ToolRegistry
from autocode.layer4.llm import LLMResponse


def _make_registry() -> ToolRegistry:
    reg = ToolRegistry()
    reg.register(ToolDefinition(
        name="read_file",
        description="Read a file",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=lambda **kw: "contents",
    ))
    return reg


def _make_tools_no_scheduler():
    """Create manager + tools registry without starting the scheduler."""
    provider = AsyncMock()
    provider.generate_with_tools = AsyncMock(return_value=LLMResponse(
        content="Done", tool_calls=[],
    ))
    scheduler = LLMScheduler()
    # Don't start — non-async tests don't need the worker
    base_reg = _make_registry()
    manager = SubagentManager(
        provider=provider,
        tool_registry=base_reg,
        scheduler=scheduler,
        max_concurrent=3,
    )
    registry = ToolRegistry()
    register_subagent_tools(registry, manager)
    return registry, manager, scheduler


def test_subagent_tools_registered():
    """All 4 subagent tools are registered."""
    registry, _, _ = _make_tools_no_scheduler()
    assert registry.get("spawn_subagent") is not None
    assert registry.get("check_subagent") is not None
    assert registry.get("cancel_subagent") is not None
    assert registry.get("list_subagents") is not None


def test_spawn_handler_requires_task():
    """spawn_subagent returns error if task is empty."""
    registry, _, _ = _make_tools_no_scheduler()
    tool = registry.get("spawn_subagent")
    assert tool is not None
    result = tool.handler(subagent_type="explore", task="")
    assert "Error" in result


@pytest.mark.asyncio
async def test_spawn_and_check_handler():
    """spawn_subagent returns ID, check_subagent returns result."""
    provider = AsyncMock()
    provider.generate_with_tools = AsyncMock(return_value=LLMResponse(
        content="Done", tool_calls=[],
    ))
    scheduler = LLMScheduler()
    scheduler.start()
    base_reg = _make_registry()
    manager = SubagentManager(
        provider=provider,
        tool_registry=base_reg,
        scheduler=scheduler,
        max_concurrent=3,
    )
    registry = ToolRegistry()
    register_subagent_tools(registry, manager)

    spawn_tool = registry.get("spawn_subagent")
    assert spawn_tool is not None
    result = spawn_tool.handler(subagent_type="explore", task="Find files")
    assert "Spawned" in result
    # Extract subagent ID from result
    sid = result.split("'")[1]

    # Wait for completion
    await asyncio.sleep(0.5)

    check_tool = registry.get("check_subagent")
    assert check_tool is not None
    check_result = check_tool.handler(subagent_id=sid)
    assert "completed" in check_result or "Done" in check_result

    await scheduler.shutdown()


def test_cancel_handler_not_found():
    """cancel_subagent for nonexistent ID returns appropriate message."""
    registry, _, _ = _make_tools_no_scheduler()
    tool = registry.get("cancel_subagent")
    assert tool is not None
    result = tool.handler(subagent_id="nonexistent")
    assert "not running" in result or "not found" in result


def test_list_handler_empty():
    """list_subagents returns empty message when none exist."""
    registry, _, _ = _make_tools_no_scheduler()
    tool = registry.get("list_subagents")
    assert tool is not None
    result = tool.handler()
    assert "No subagents" in result
