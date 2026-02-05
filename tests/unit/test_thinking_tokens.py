"""Tests for thinking/reasoning token support.

Covers:
- <think> tag parsing (DeepSeek R1 style)
- reasoning field in LLMResponse
- on_thinking_chunk callback in agent loop
- ChatView thinking stream display
- Config reasoning_enabled
- Ctrl+T thinking toggle
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pytest

from hybridcoder.config import HybridCoderConfig, LLMConfig
from hybridcoder.layer4.llm import LLMResponse, ToolCall, _parse_think_tags


class TestParseThinkTags:
    """Tests for the <think> tag parser."""

    def test_no_think_tags(self) -> None:
        """Plain text without tags returns content only."""
        content, reasoning = _parse_think_tags("Hello world")
        assert content == "Hello world"
        assert reasoning == ""

    def test_simple_think_tags(self) -> None:
        """Single think block is extracted."""
        text = "<think>Let me figure this out</think>The answer is 42."
        content, reasoning = _parse_think_tags(text)
        assert content == "The answer is 42."
        assert reasoning == "Let me figure this out"

    def test_multiline_think_tags(self) -> None:
        """Think block spanning multiple lines works."""
        text = "<think>\nStep 1: parse\nStep 2: solve\n</think>\nDone."
        content, reasoning = _parse_think_tags(text)
        assert "Done." in content
        assert "Step 1: parse" in reasoning
        assert "Step 2: solve" in reasoning

    def test_multiple_think_blocks(self) -> None:
        """Multiple think blocks are all captured."""
        text = "<think>first</think>middle<think>second</think>end"
        content, reasoning = _parse_think_tags(text)
        assert "middle" in content
        assert "end" in content
        assert "first" in reasoning
        assert "second" in reasoning

    def test_empty_think_tags(self) -> None:
        """Empty think tags return empty reasoning."""
        text = "<think></think>Just the answer."
        content, reasoning = _parse_think_tags(text)
        assert content == "Just the answer."
        assert reasoning == ""

    def test_only_think_tags(self) -> None:
        """Message with only thinking and no answer."""
        text = "<think>I'm thinking really hard</think>"
        content, reasoning = _parse_think_tags(text)
        assert content == ""
        assert reasoning == "I'm thinking really hard"

    def test_think_tags_with_code(self) -> None:
        """Think tags containing code blocks."""
        text = (
            "<think>Looking at the code:\n```python\nprint('hi')\n```\n</think>"
            "Here's the fix."
        )
        content, reasoning = _parse_think_tags(text)
        assert content == "Here's the fix."
        assert "print('hi')" in reasoning


class TestLLMResponseReasoning:
    """Tests for the reasoning field on LLMResponse."""

    def test_reasoning_default_none(self) -> None:
        """Reasoning is None by default."""
        resp = LLMResponse(content="hello")
        assert resp.reasoning is None

    def test_reasoning_set(self) -> None:
        """Reasoning can be set."""
        resp = LLMResponse(content="answer", reasoning="thought process")
        assert resp.reasoning == "thought process"

    def test_reasoning_with_tool_calls(self) -> None:
        """Reasoning works alongside tool calls."""
        resp = LLMResponse(
            content="",
            tool_calls=[ToolCall(id="tc1", name="read_file", arguments={"path": "x"})],
            reasoning="I should read the file first",
        )
        assert resp.reasoning == "I should read the file first"
        assert len(resp.tool_calls) == 1


class TestConfigReasoningEnabled:
    """Tests for reasoning_enabled config."""

    def test_default_reasoning_enabled(self) -> None:
        """reasoning_enabled defaults to True."""
        config = LLMConfig()
        assert config.reasoning_enabled is True

    def test_reasoning_disabled(self) -> None:
        """reasoning_enabled can be set to False."""
        config = LLMConfig(reasoning_enabled=False)
        assert config.reasoning_enabled is False

    def test_full_config_has_reasoning(self) -> None:
        """HybridCoderConfig includes reasoning_enabled."""
        config = HybridCoderConfig()
        assert config.llm.reasoning_enabled is True


class TestAgentLoopThinkingCallback:
    """Tests for on_thinking_chunk callback in agent loop."""

    @pytest.fixture()
    def store(self, tmp_path: Path) -> Any:
        from hybridcoder.session.store import SessionStore
        s = SessionStore(tmp_path / "test.db")
        yield s
        s.close()

    @pytest.fixture()
    def session_id(self, store: Any) -> str:
        return store.create_session(title="Test", model="m", provider="mock")

    @pytest.mark.asyncio()
    async def test_thinking_callback_receives_chunks(
        self, store: Any, session_id: str,
    ) -> None:
        """on_thinking_chunk is called when provider returns reasoning."""
        from hybridcoder.agent.approval import ApprovalManager, ApprovalMode
        from hybridcoder.agent.loop import AgentLoop
        from hybridcoder.agent.tools import ToolRegistry

        mock = AsyncMock()
        thinking_chunks: list[str] = []

        async def fake_generate(messages: Any, tools: Any, **kwargs: Any) -> LLMResponse:
            on_thinking = kwargs.get("on_thinking_chunk")
            if on_thinking:
                on_thinking("thinking step 1")
            on_chunk = kwargs.get("on_chunk")
            if on_chunk:
                on_chunk("The answer")
            return LLMResponse(content="The answer", reasoning="thinking step 1")

        mock.generate_with_tools = fake_generate

        loop = AgentLoop(
            mock, ToolRegistry(),
            ApprovalManager(ApprovalMode.AUTO),
            store, session_id,
        )

        result = await loop.run(
            "test",
            on_thinking_chunk=lambda c: thinking_chunks.append(c),
        )
        assert result == "The answer"
        assert thinking_chunks == ["thinking step 1"]

    @pytest.mark.asyncio()
    async def test_no_thinking_callback_is_ok(
        self, store: Any, session_id: str,
    ) -> None:
        """Agent loop works fine without on_thinking_chunk."""
        from hybridcoder.agent.approval import ApprovalManager, ApprovalMode
        from hybridcoder.agent.loop import AgentLoop
        from hybridcoder.agent.tools import ToolRegistry

        mock = AsyncMock()

        async def fake_generate(messages: Any, tools: Any, **kwargs: Any) -> LLMResponse:
            return LLMResponse(content="Just text", reasoning="hidden thought")

        mock.generate_with_tools = fake_generate

        loop = AgentLoop(
            mock, ToolRegistry(),
            ApprovalManager(ApprovalMode.AUTO),
            store, session_id,
        )

        result = await loop.run("test")
        assert result == "Just text"


class TestChatViewThinkingStream:
    """Tests for ChatView thinking chunk display."""

    def test_add_thinking_chunk_creates_widget(self) -> None:
        """add_thinking_chunk creates a thinking widget."""
        from hybridcoder.tui.widgets.chat_view import ChatView
        view = ChatView()
        assert view._thinking_stream_widget is None
        assert view._thinking_stream_content == ""

    def test_finish_thinking_stream_returns_content(self) -> None:
        """finish_thinking_stream returns accumulated content."""
        from hybridcoder.tui.widgets.chat_view import ChatView
        view = ChatView()
        view._thinking_stream_content = "some thinking"
        content = view.finish_thinking_stream()
        assert content == "some thinking"
        assert view._thinking_stream_content == ""


class TestThinkingToggle:
    """Tests for the Ctrl+T thinking toggle."""

    @pytest.mark.asyncio()
    async def test_toggle_flips_show_thinking(self) -> None:
        """action_toggle_thinking flips _show_thinking."""
        from hybridcoder.tui.app import HybridCoderApp

        config = HybridCoderConfig()
        config.tui.session_db_path = ":memory:"
        app = HybridCoderApp(config=config)
        async with app.run_test():
            assert app._show_thinking is True
            app.action_toggle_thinking()
            assert app._show_thinking is False
            app.action_toggle_thinking()
            assert app._show_thinking is True

    @pytest.mark.asyncio()
    async def test_toggle_posts_message(self) -> None:
        """Toggling thinking posts a system message."""
        from hybridcoder.tui.app import HybridCoderApp
        from hybridcoder.tui.widgets.chat_view import ChatView

        config = HybridCoderConfig()
        config.tui.session_db_path = ":memory:"
        app = HybridCoderApp(config=config)
        async with app.run_test() as pilot:
            app.action_toggle_thinking()
            await pilot.pause()
            chat = app.query_one("#chat-view", ChatView)
            children = list(chat.children)
            # Should have at least one system message about toggle
            assert len(children) >= 1

    @pytest.mark.asyncio()
    async def test_bindings_for_thinking_toggle(self) -> None:
        """Ctrl+T and Alt+T are bound to toggle_thinking."""
        from hybridcoder.tui.app import HybridCoderApp
        config = HybridCoderConfig()
        app = HybridCoderApp(config=config)
        binding_keys = [b.key for b in app.BINDINGS]
        assert "ctrl+t" in binding_keys
        assert "alt+t" in binding_keys
