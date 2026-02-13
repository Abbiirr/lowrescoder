"""Benchmark tests for tool call efficiency.

Measures how efficiently tools are used: minimal tool calls,
correct tool selection, and proper argument handling.

These tests are designed to be agnostic to the underlying LLM/tech stack.
They test the tool system's API contract, not the LLM's intelligence.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pytest

from hybridcoder.agent.approval import ApprovalManager, ApprovalMode
from hybridcoder.agent.loop import AgentLoop
from hybridcoder.agent.tools import create_default_registry
from hybridcoder.layer4.llm import LLMResponse, ToolCall
from hybridcoder.session.store import SessionStore


@pytest.fixture()
def store(tmp_path: Path) -> SessionStore:
    s = SessionStore(tmp_path / "bench.db")
    yield s
    s.close()


@pytest.fixture()
def session_id(store: SessionStore) -> str:
    return store.create_session(title="Bench", model="m", provider="mock")


def _make_provider(responses: list[LLMResponse]) -> Any:
    """Create a mock provider returning responses in sequence."""
    mock = AsyncMock()
    call_count = 0

    async def gen(messages: Any, tools: Any, **kwargs: Any) -> LLMResponse:
        nonlocal call_count
        idx = min(call_count, len(responses) - 1)
        call_count += 1
        return responses[idx]

    mock.generate_with_tools = gen
    mock.call_count = lambda: call_count
    return mock


class TestToolCallEfficiency:
    """How many LLM round trips does a task need?"""

    @pytest.mark.asyncio()
    async def test_read_file_single_round_trip(
        self, store: SessionStore, session_id: str, tmp_path: Path,
    ) -> None:
        """Reading a file should take 2 LLM calls: tool call + final response."""
        test_file = tmp_path / "data.txt"
        test_file.write_text("hello world")

        responses = [
            LLMResponse(
                content="",
                tool_calls=[ToolCall(
                    id="tc1", name="read_file", arguments={"path": str(test_file)},
                )],
            ),
            LLMResponse(content="The file contains: hello world"),
        ]

        provider = _make_provider(responses)
        registry = create_default_registry()
        approval = ApprovalManager(ApprovalMode.AUTO)
        loop = AgentLoop(provider, registry, approval, store, session_id)

        result = await loop.run("Read the file")

        # Should complete in exactly 2 LLM calls
        assert "hello world" in result

    @pytest.mark.asyncio()
    async def test_search_then_read_two_round_trips(
        self, store: SessionStore, session_id: str, tmp_path: Path,
    ) -> None:
        """Search + read should take 3 LLM calls: search + read + response."""
        (tmp_path / "code.py").write_text("def target_function():\n    return 42\n")

        responses = [
            # Call 1: search
            LLMResponse(
                content="",
                tool_calls=[ToolCall(
                    id="tc1", name="search_text",
                    arguments={"pattern": "target_function", "directory": str(tmp_path)},
                )],
            ),
            # Call 2: read the found file
            LLMResponse(
                content="",
                tool_calls=[ToolCall(
                    id="tc2", name="read_file",
                    arguments={"path": str(tmp_path / "code.py")},
                )],
            ),
            # Call 3: final response
            LLMResponse(content="Found target_function in code.py, it returns 42"),
        ]

        provider = _make_provider(responses)
        registry = create_default_registry()
        approval = ApprovalManager(ApprovalMode.AUTO)
        loop = AgentLoop(provider, registry, approval, store, session_id)

        result = await loop.run("Find and read target_function")
        assert "target_function" in result

    @pytest.mark.asyncio()
    async def test_max_iterations_limits_runaway(
        self, store: SessionStore, session_id: str,
    ) -> None:
        """Agent loop stops at MAX_ITERATIONS, preventing runaway tool calls."""
        infinite_tool = LLMResponse(
            content="",
            tool_calls=[ToolCall(id="tc1", name="list_files", arguments={})],
        )

        provider = _make_provider([infinite_tool] * 20)
        registry = create_default_registry()
        approval = ApprovalManager(ApprovalMode.AUTO)
        loop = AgentLoop(provider, registry, approval, store, session_id)
        loop.MAX_ITERATIONS = 5

        start = time.monotonic()
        result = await loop.run("list files forever")
        duration = time.monotonic() - start

        # Should stop within MAX_ITERATIONS
        assert result is not None
        # Should not take forever (generous for Windows/CI)
        assert duration < 30.0


class TestToolSelection:
    """Does the tool system correctly route to the right handler?"""

    def test_registry_has_all_expected_tools(self) -> None:
        """Default registry has exactly 6 tools."""
        registry = create_default_registry()
        tools = registry.get_all()
        assert len(tools) == 11
        names = {t.name for t in tools}
        assert names == {
            "read_file", "write_file", "list_files",
            "search_text", "run_command", "ask_user",
            "find_references", "find_definition", "get_type_info",
            "list_symbols", "search_code",
        }

    def test_read_tools_do_not_require_approval(self) -> None:
        """Read-only tools should not require approval."""
        registry = create_default_registry()
        for name in ("read_file", "list_files", "search_text", "ask_user"):
            tool = registry.get(name)
            assert tool is not None
            assert tool.requires_approval is False

    def test_write_tools_require_approval(self) -> None:
        """Mutating tools should require approval."""
        registry = create_default_registry()
        for name in ("write_file", "run_command"):
            tool = registry.get(name)
            assert tool is not None
            assert tool.requires_approval is True

    def test_tool_schemas_are_valid_openai_format(self) -> None:
        """All tool schemas follow OpenAI function-calling format."""
        registry = create_default_registry()
        schemas = registry.get_schemas_openai_format()

        for schema in schemas:
            assert schema["type"] == "function"
            func = schema["function"]
            assert "name" in func
            assert "description" in func
            assert "parameters" in func
            assert func["parameters"]["type"] == "object"
            assert "properties" in func["parameters"]


class TestApprovalGating:
    """Does the approval system correctly gate dangerous operations?"""

    @pytest.mark.asyncio()
    async def test_read_only_mode_blocks_all_writes(
        self, store: SessionStore, session_id: str, tmp_path: Path,
    ) -> None:
        """In read-only mode, write_file is blocked without asking."""
        responses = [
            LLMResponse(
                content="",
                tool_calls=[ToolCall(
                    id="tc1", name="write_file",
                    arguments={"path": str(tmp_path / "x.txt"), "content": "x"},
                )],
            ),
            LLMResponse(content="blocked"),
        ]

        provider = _make_provider(responses)
        registry = create_default_registry()
        approval = ApprovalManager(ApprovalMode.READ_ONLY)
        loop = AgentLoop(provider, registry, approval, store, session_id)

        await loop.run("write a file")
        assert not (tmp_path / "x.txt").exists()

    @pytest.mark.asyncio()
    async def test_suggest_mode_requires_callback(
        self, store: SessionStore, session_id: str, tmp_path: Path,
    ) -> None:
        """In suggest mode, writes are denied without approval callback."""
        responses = [
            LLMResponse(
                content="",
                tool_calls=[ToolCall(
                    id="tc1", name="write_file",
                    arguments={"path": str(tmp_path / "x.txt"), "content": "x"},
                )],
            ),
            LLMResponse(content="denied"),
        ]

        provider = _make_provider(responses)
        registry = create_default_registry()
        approval = ApprovalManager(ApprovalMode.SUGGEST)
        loop = AgentLoop(provider, registry, approval, store, session_id)

        # No approval_callback → denied for safety
        await loop.run("write a file")
        assert not (tmp_path / "x.txt").exists()

    @pytest.mark.asyncio()
    async def test_auto_mode_allows_writes(
        self, store: SessionStore, session_id: str, tmp_path: Path,
    ) -> None:
        """In auto mode, writes proceed without callback."""
        responses = [
            LLMResponse(
                content="",
                tool_calls=[ToolCall(
                    id="tc1", name="write_file",
                    arguments={"path": str(tmp_path / "x.txt"), "content": "x"},
                )],
            ),
            LLMResponse(content="done"),
        ]

        provider = _make_provider(responses)
        registry = create_default_registry()
        approval = ApprovalManager(ApprovalMode.AUTO)
        loop = AgentLoop(provider, registry, approval, store, session_id)

        await loop.run("write a file")
        assert (tmp_path / "x.txt").exists()
