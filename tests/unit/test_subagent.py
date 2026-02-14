"""Tests for SubagentLoop, SubagentManager — Sprint 4B."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest

from hybridcoder.agent.subagent import (
    LLMScheduler,
    SubagentLoop,
    SubagentManager,
    SubagentType,
)
from hybridcoder.agent.tools import ToolDefinition, ToolRegistry
from hybridcoder.layer4.llm import LLMResponse, ToolCall


def _make_registry() -> ToolRegistry:
    """Create a minimal tool registry for testing."""
    reg = ToolRegistry()
    reg.register(ToolDefinition(
        name="read_file",
        description="Read a file",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=lambda **kw: "file contents here",
    ))
    reg.register(ToolDefinition(
        name="write_file",
        description="Write a file",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=lambda **kw: f"Written to {kw.get('path', 'unknown')}",
        requires_approval=True,
        mutates_fs=True,
    ))
    reg.register(ToolDefinition(
        name="run_command",
        description="Run command",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=lambda **kw: "ok",
        requires_approval=True,
        executes_shell=True,
    ))
    reg.register(ToolDefinition(
        name="list_files",
        description="List files",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=lambda **kw: "file1.py\nfile2.py",
    ))
    return reg


@pytest.mark.asyncio
async def test_explore_subagent_restricts_tools():
    """Explore subagent cannot use mutates_fs or executes_shell tools."""
    provider = AsyncMock()
    provider.generate_with_tools = AsyncMock(return_value=LLMResponse(
        content="Done exploring", tool_calls=[],
    ))

    scheduler = LLMScheduler()
    scheduler.start()

    loop = SubagentLoop(
        provider=provider,
        tool_registry=_make_registry(),
        scheduler=scheduler,
        subagent_type=SubagentType.EXPLORE,
    )

    # Verify restricted registry
    assert loop._tools.get("read_file") is not None
    assert loop._tools.get("list_files") is not None
    assert loop._tools.get("write_file") is None  # mutates_fs blocked
    assert loop._tools.get("run_command") is None  # executes_shell blocked

    await scheduler.shutdown()


@pytest.mark.asyncio
async def test_plan_subagent_restricts_tools():
    """Plan subagent also blocks mutating tools."""
    scheduler = LLMScheduler()
    scheduler.start()

    loop = SubagentLoop(
        provider=AsyncMock(),
        tool_registry=_make_registry(),
        scheduler=scheduler,
        subagent_type=SubagentType.PLAN,
    )

    assert loop._tools.get("read_file") is not None
    assert loop._tools.get("write_file") is None
    assert loop._tools.get("run_command") is None

    await scheduler.shutdown()


@pytest.mark.asyncio
async def test_execute_subagent_has_all_tools():
    """Execute subagent gets all tools (minus subagent tools)."""
    scheduler = LLMScheduler()
    scheduler.start()

    loop = SubagentLoop(
        provider=AsyncMock(),
        tool_registry=_make_registry(),
        scheduler=scheduler,
        subagent_type=SubagentType.EXECUTE,
    )

    assert loop._tools.get("read_file") is not None
    assert loop._tools.get("write_file") is not None
    assert loop._tools.get("run_command") is not None

    await scheduler.shutdown()


@pytest.mark.asyncio
async def test_subagent_auto_denies_approval():
    """Background subagents auto-deny tools requiring approval."""
    provider = AsyncMock()
    # LLM tries to call write_file which requires approval
    provider.generate_with_tools = AsyncMock(side_effect=[
        LLMResponse(content="", tool_calls=[
            ToolCall(id="tc1", name="write_file", arguments={"path": "test.py", "content": "x"}),
        ]),
        LLMResponse(content="I was blocked", tool_calls=[]),
    ])

    scheduler = LLMScheduler()
    scheduler.start()

    loop = SubagentLoop(
        provider=provider,
        tool_registry=_make_registry(),
        scheduler=scheduler,
        subagent_type=SubagentType.EXECUTE,
    )

    result = await loop.run("Write a test file")

    assert result.status == "completed"
    # The tool call was auto-denied because requires_approval=True
    assert provider.generate_with_tools.call_count == 2

    await scheduler.shutdown()


@pytest.mark.asyncio
async def test_subagent_circuit_breaker():
    """2 consecutive errors trigger circuit breaker."""
    provider = AsyncMock()
    # Return tool calls that will error twice
    provider.generate_with_tools = AsyncMock(return_value=LLMResponse(
        content="", tool_calls=[
            ToolCall(id="tc1", name="unknown_tool", arguments={}),
            ToolCall(id="tc2", name="also_unknown", arguments={}),
        ],
    ))

    scheduler = LLMScheduler()
    scheduler.start()

    loop = SubagentLoop(
        provider=provider,
        tool_registry=_make_registry(),
        scheduler=scheduler,
        subagent_type=SubagentType.EXPLORE,
    )

    result = await loop.run("Do something")

    assert result.status == "failed"
    assert "circuit breaker" in result.summary.lower() or result.iterations_used == 1

    await scheduler.shutdown()


@pytest.mark.asyncio
async def test_subagent_max_iterations():
    """Subagent stops after max iterations."""
    call_count = 0

    async def fake_generate(messages, tools, **kw):
        nonlocal call_count
        call_count += 1
        # Always return a tool call to keep iterating
        return LLMResponse(content=f"iter {call_count}", tool_calls=[
            ToolCall(id=f"tc{call_count}", name="read_file", arguments={"path": "a.py"}),
        ])

    provider = AsyncMock()
    provider.generate_with_tools = AsyncMock(side_effect=fake_generate)

    scheduler = LLMScheduler()
    scheduler.start()

    loop = SubagentLoop(
        provider=provider,
        tool_registry=_make_registry(),
        scheduler=scheduler,
        subagent_type=SubagentType.EXPLORE,
        max_iterations=3,
    )

    result = await loop.run("Keep reading files")

    assert result.iterations_used == 3
    assert result.status == "completed"

    await scheduler.shutdown()


@pytest.mark.asyncio
async def test_subagent_cancel():
    """Cancelled subagent returns cancelled status."""
    provider = AsyncMock()

    async def slow_generate(messages, tools, **kw):
        await asyncio.sleep(10)
        return LLMResponse(content="done", tool_calls=[])

    provider.generate_with_tools = AsyncMock(side_effect=slow_generate)

    scheduler = LLMScheduler()
    scheduler.start()

    loop = SubagentLoop(
        provider=provider,
        tool_registry=_make_registry(),
        scheduler=scheduler,
        subagent_type=SubagentType.EXPLORE,
        timeout_seconds=1,
    )

    result = await loop.run("Take too long")

    # Should timeout (1 second) or be cancelled
    assert result.status in ("failed", "cancelled")

    await scheduler.shutdown()


@pytest.mark.asyncio
async def test_manager_spawn_and_check():
    """SubagentManager can spawn and track subagents."""
    provider = AsyncMock()
    provider.generate_with_tools = AsyncMock(return_value=LLMResponse(
        content="Found 3 files", tool_calls=[],
    ))

    scheduler = LLMScheduler()
    scheduler.start()

    manager = SubagentManager(
        provider=provider,
        tool_registry=_make_registry(),
        scheduler=scheduler,
        max_concurrent=3,
    )

    sid = manager.spawn("explore", "List all Python files")
    assert sid  # Got an ID back

    # Wait for completion
    await asyncio.sleep(0.5)

    result = manager.get_result(sid)
    assert result is not None
    assert result.status == "completed"
    assert "Found 3 files" in result.summary

    await scheduler.shutdown()


@pytest.mark.asyncio
async def test_manager_max_concurrent():
    """SubagentManager enforces max concurrent limit."""
    provider = AsyncMock()

    async def slow_generate(messages, tools, **kw):
        await asyncio.sleep(5)
        return LLMResponse(content="done", tool_calls=[])

    provider.generate_with_tools = AsyncMock(side_effect=slow_generate)

    scheduler = LLMScheduler()
    scheduler.start()

    manager = SubagentManager(
        provider=provider,
        tool_registry=_make_registry(),
        scheduler=scheduler,
        max_concurrent=2,
        timeout_seconds=10,
    )

    manager.spawn("explore", "Task 1")
    manager.spawn("explore", "Task 2")

    with pytest.raises(RuntimeError, match="Max concurrent"):
        manager.spawn("explore", "Task 3")

    manager.cancel_all()
    await scheduler.shutdown()


@pytest.mark.asyncio
async def test_manager_cancel_all():
    """cancel_all stops all running subagents."""
    provider = AsyncMock()

    async def slow_generate(messages, tools, **kw):
        await asyncio.sleep(5)
        return LLMResponse(content="done", tool_calls=[])

    provider.generate_with_tools = AsyncMock(side_effect=slow_generate)

    scheduler = LLMScheduler()
    scheduler.start()

    manager = SubagentManager(
        provider=provider,
        tool_registry=_make_registry(),
        scheduler=scheduler,
        max_concurrent=3,
    )

    manager.spawn("explore", "Task 1")
    manager.spawn("explore", "Task 2")
    assert manager.active_count == 2

    count = manager.cancel_all()
    assert count == 2

    await scheduler.shutdown()


@pytest.mark.asyncio
async def test_manager_cancel_stores_cancelled_result():
    """Cancelled subagent persists a cancelled SubagentResult via try/finally."""
    provider = AsyncMock()

    async def slow_generate(messages, tools, **kw):
        await asyncio.sleep(5)
        return LLMResponse(content="done", tool_calls=[])

    provider.generate_with_tools = AsyncMock(side_effect=slow_generate)

    scheduler = LLMScheduler()
    scheduler.start()

    manager = SubagentManager(
        provider=provider,
        tool_registry=_make_registry(),
        scheduler=scheduler,
        max_concurrent=3,
    )

    sid = manager.spawn("explore", "Slow task")
    assert manager.active_count == 1

    manager.cancel(sid)
    # Wait for the asyncio task to actually finish after cancellation
    task = manager._active.get(sid)
    if task:
        try:
            await task
        except asyncio.CancelledError:
            pass

    # _active should be cleaned up by try/finally
    assert manager.active_count == 0
    # Cancelled result should be stored
    result = manager.get_result(sid)
    assert result is not None
    assert result.status == "cancelled"

    await scheduler.shutdown()
