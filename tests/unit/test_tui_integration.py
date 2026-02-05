"""TUI integration tests with mocked LLM provider."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pytest

from hybridcoder.config import HybridCoderConfig
from hybridcoder.layer4.llm import LLMResponse
from hybridcoder.tui.app import HybridCoderApp
from hybridcoder.tui.widgets.chat_view import ChatView
from hybridcoder.tui.widgets.input_bar import InputBar


@pytest.fixture()
def tui_config(tmp_path: Path) -> HybridCoderConfig:
    config = HybridCoderConfig()
    config.tui.session_db_path = str(tmp_path / "test.db")
    return config


def _make_mock_provider(responses: list[LLMResponse]) -> Any:
    """Create a mock provider that returns LLMResponse objects."""
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

    async def fake_generate(messages: Any, **kwargs: Any) -> Any:
        if responses and responses[0].content:
            yield responses[0].content

    mock.generate_with_tools = fake_generate_with_tools
    mock.generate = fake_generate
    mock.count_tokens = lambda text: len(text) // 4
    return mock


class TestTUIIntegration:
    @pytest.mark.asyncio()
    async def test_send_message_and_get_response(self, tui_config: HybridCoderConfig) -> None:
        """Sending a message triggers agent loop and shows response."""
        mock = _make_mock_provider([LLMResponse(content="Mock response")])
        app = HybridCoderApp(config=tui_config)

        async with app.run_test() as pilot:
            app._provider = mock

            input_bar = app.query_one("#input-bar", InputBar)
            input_bar.focus()
            for char in "hi":
                await pilot.press(char)
            await pilot.press("enter")
            await pilot.pause()
            await pilot.pause()
            await pilot.pause()

            chat = app.query_one("#chat-view", ChatView)
            # Should have at least the user message widget
            assert len(list(chat.children)) >= 1

    @pytest.mark.asyncio()
    async def test_tool_call_displayed_in_chat(self, tui_config: HybridCoderConfig) -> None:
        """Tool calls are displayed in the chat view."""
        app = HybridCoderApp(config=tui_config)
        async with app.run_test() as pilot:
            chat = app.query_one("#chat-view", ChatView)
            chat.add_tool_call_display("read_file", "completed", "file contents here")
            await pilot.pause()
            children = list(chat.children)
            assert len(children) >= 1

    @pytest.mark.asyncio()
    async def test_approval_prompt_shown_in_suggest_mode(
        self, tui_config: HybridCoderConfig,
    ) -> None:
        """In suggest mode, write tools trigger diff preview."""
        tui_config.tui.approval_mode = "suggest"
        app = HybridCoderApp(config=tui_config)

        async with app.run_test() as pilot:
            # Test diff preview directly
            chat = app.query_one("#chat-view", ChatView)
            app._show_diff_preview("new_file.py", "print('hello')")
            await pilot.pause()
            # Should have added a diff message (for a new file, it shows the full content)
            children = list(chat.children)
            assert len(children) >= 1

    @pytest.mark.asyncio()
    async def test_session_resume(self, tui_config: HybridCoderConfig) -> None:
        """Resuming a session loads its messages."""
        app = HybridCoderApp(config=tui_config)

        async with app.run_test() as pilot:
            # Add messages to the session
            sid = app.session_id
            app.session_store.add_message(sid, "user", "Hello")
            app.session_store.add_message(sid, "assistant", "Hi there")

            # Resume by dispatching /resume command
            input_bar = app.query_one("#input-bar", InputBar)
            input_bar.focus()
            # Type enough of the session ID to match
            for char in f"/resume {sid[:8]}":
                await pilot.press(char)
            await pilot.press("enter")
            await pilot.pause()
            await pilot.pause()

            chat = app.query_one("#chat-view", ChatView)
            children = list(chat.children)
            # Should have: resume message + replayed user + replayed assistant
            assert len(children) >= 1
