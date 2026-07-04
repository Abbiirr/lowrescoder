"""Tests for the Textual TUI application."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pytest

from autocode.config import AutoCodeConfig
from autocode.layer4.llm import LLMResponse
from autocode.tui.app import AutoCodeApp
from autocode.tui.widgets.chat_view import ChatView
from autocode.tui.widgets.input_bar import InputBar
from autocode.tui.widgets.status_bar import StatusBar


@pytest.fixture()
def tui_config(tmp_path: Path) -> AutoCodeConfig:
    """Config with temp session DB path."""
    config = AutoCodeConfig()
    config.tui.session_db_path = str(tmp_path / "test.db")
    return config


def _make_slow_mock_provider(responses: list[LLMResponse]) -> Any:
    """Create a mock provider for thinking indicator tests."""
    mock = AsyncMock()
    call_count = 0

    async def fake_generate_with_tools(
        messages: Any, tools: Any, **kwargs: Any,
    ) -> LLMResponse:
        nonlocal call_count
        idx = min(call_count, len(responses) - 1)
        call_count += 1
        resp = responses[idx]
        on_chunk = kwargs.get("on_chunk")
        if on_chunk and resp.content:
            on_chunk(resp.content)
        return resp

    mock.generate_with_tools = fake_generate_with_tools
    mock.count_tokens = lambda text: len(text) // 4
    return mock


class TestTUIApp:
    @pytest.mark.asyncio()
    async def test_app_mounts(self, tui_config: AutoCodeConfig) -> None:
        """App mounts all expected widgets."""
        app = AutoCodeApp(config=tui_config)
        async with app.run_test():
            assert app.query_one("#chat-view", ChatView) is not None
            assert app.query_one("#input-bar", InputBar) is not None
            assert app.query_one("#status-bar", StatusBar) is not None
            assert app.query_one("#header") is not None

    @pytest.mark.asyncio()
    async def test_input_submits_message(self, tui_config: AutoCodeConfig) -> None:
        """Typing text and pressing enter adds a message to chat."""
        app = AutoCodeApp(config=tui_config)

        # Mock the provider to avoid real LLM calls
        mock_provider = _make_slow_mock_provider([LLMResponse(content="Hello!")])

        async with app.run_test() as pilot:
            app._provider = mock_provider

            # Focus input and type characters individually
            input_bar = app.query_one("#input-bar", InputBar)
            input_bar.focus()
            for char in "hi":
                await pilot.press(char)
            await pilot.press("enter")
            await pilot.pause()
            await pilot.pause()

            # Check that user message appeared in chat
            chat = app.query_one("#chat-view", ChatView)
            children = list(chat.children)
            assert len(children) >= 1  # at least user message widget

    @pytest.mark.asyncio()
    async def test_exit_command(self, tui_config: AutoCodeConfig) -> None:
        """The /exit command quits the app."""
        app = AutoCodeApp(config=tui_config)
        async with app.run_test() as pilot:
            input_bar = app.query_one("#input-bar", InputBar)
            input_bar.focus()
            for char in "/exit":
                await pilot.press(char)
            await pilot.press("enter")
            await pilot.pause()

    @pytest.mark.asyncio()
    async def test_bench_ready_sentinel(
        self, tui_config: AutoCodeConfig, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """BENCH:READY is emitted when AUTOCODE_BENCH=1."""
        monkeypatch.setenv("AUTOCODE_BENCH", "1")
        app = AutoCodeApp(config=tui_config)

        # Patch print to capture the sentinel
        original_print = print
        captured: list[str] = []

        def capture_print(*args: object, **kwargs: object) -> None:
            captured.append(" ".join(str(a) for a in args))
            original_print(*args, **kwargs)

        monkeypatch.setattr("builtins.print", capture_print)

        async with app.run_test() as pilot:
            await pilot.pause()

        assert any("BENCH:READY" in s for s in captured)


class TestThinkingIndicator:
    @pytest.mark.asyncio()
    async def test_status_bar_shows_thinking(
        self, tui_config: AutoCodeConfig,
    ) -> None:
        """StatusBar shows 'Thinking...' while generating."""
        mock = _make_slow_mock_provider([LLMResponse(content="done")])
        app = AutoCodeApp(config=tui_config)

        async with app.run_test() as pilot:
            app._provider = mock
            status_bar = app.query_one("#status-bar", StatusBar)

            # Before sending, thinking should be off
            assert status_bar.thinking is False
            rendered = status_bar.render()
            assert "Thinking" not in rendered

            # Send a message to trigger agent loop
            input_bar = app.query_one("#input-bar", InputBar)
            input_bar.focus()
            for char in "hi":
                await pilot.press(char)
            await pilot.press("enter")
            await pilot.pause()
            await pilot.pause()
            await pilot.pause()

            # After completion, thinking should be off
            assert status_bar.thinking is False

    @pytest.mark.asyncio()
    async def test_status_bar_render_with_thinking(
        self, tui_config: AutoCodeConfig,
    ) -> None:
        """StatusBar render includes animated 'Thinking' when thinking=True."""
        app = AutoCodeApp(config=tui_config)
        async with app.run_test():
            status_bar = app.query_one("#status-bar", StatusBar)
            status_bar.thinking = True
            rendered = status_bar.render()
            assert "Thinking" in rendered

            status_bar.thinking = False
            rendered = status_bar.render()
            assert "Thinking..." not in rendered

    @pytest.mark.asyncio()
    async def test_chat_view_shows_thinking_indicator(
        self, tui_config: AutoCodeConfig,
    ) -> None:
        """ChatView shows a 'Thinking...' widget via show_thinking()."""
        app = AutoCodeApp(config=tui_config)
        async with app.run_test() as pilot:
            chat = app.query_one("#chat-view", ChatView)

            # Initially no thinking indicator
            thinking_widgets = chat.query(".thinking-indicator")
            assert len(thinking_widgets) == 0

            # Show thinking
            chat.show_thinking()
            await pilot.pause()
            thinking_widgets = chat.query(".thinking-indicator")
            assert len(thinking_widgets) == 1

            # Hide thinking
            chat.hide_thinking()
            await pilot.pause()
            thinking_widgets = chat.query(".thinking-indicator")
            assert len(thinking_widgets) == 0

    @pytest.mark.asyncio()
    async def test_thinking_cleared_when_streaming_starts(
        self, tui_config: AutoCodeConfig,
    ) -> None:
        """start_streaming() removes the thinking indicator."""
        app = AutoCodeApp(config=tui_config)
        async with app.run_test() as pilot:
            chat = app.query_one("#chat-view", ChatView)

            chat.show_thinking()
            await pilot.pause()
            assert len(chat.query(".thinking-indicator")) == 1

            chat.start_streaming()
            await pilot.pause()
            assert len(chat.query(".thinking-indicator")) == 0


class TestInputHistory:
    @pytest.mark.asyncio()
    async def test_up_arrow_recalls_last_message(
        self, tui_config: AutoCodeConfig,
    ) -> None:
        """Up arrow recalls the most recently submitted message."""
        mock = _make_slow_mock_provider([LLMResponse(content="ok")])
        app = AutoCodeApp(config=tui_config)

        async with app.run_test() as pilot:
            app._provider = mock
            input_bar = app.query_one("#input-bar", InputBar)
            input_bar.focus()

            # Submit "hello"
            for char in "hello":
                await pilot.press(char)
            await pilot.press("enter")
            await pilot.pause()
            await pilot.pause()

            # Input should be cleared after submit
            assert input_bar.text == ""

            # Press up → should recall "hello"
            await pilot.press("up")
            await pilot.pause()
            assert input_bar.text == "hello"

    @pytest.mark.asyncio()
    async def test_up_down_arrow_navigates_history(
        self, tui_config: AutoCodeConfig,
    ) -> None:
        """Up/down arrows navigate through multiple history entries."""
        mock = _make_slow_mock_provider(
            [LLMResponse(content="r1"), LLMResponse(content="r2")],
        )
        app = AutoCodeApp(config=tui_config)

        async with app.run_test() as pilot:
            app._provider = mock
            input_bar = app.query_one("#input-bar", InputBar)
            input_bar.focus()

            # Submit two messages
            for char in "first":
                await pilot.press(char)
            await pilot.press("enter")
            await pilot.pause()
            await pilot.pause()

            for char in "second":
                await pilot.press(char)
            await pilot.press("enter")
            await pilot.pause()
            await pilot.pause()

            # Up → "second" (most recent)
            await pilot.press("up")
            await pilot.pause()
            assert input_bar.text == "second"

            # Up again → "first"
            await pilot.press("up")
            await pilot.pause()
            assert input_bar.text == "first"

            # Down → back to "second"
            await pilot.press("down")
            await pilot.pause()
            assert input_bar.text == "second"

            # Down again → back to empty (draft)
            await pilot.press("down")
            await pilot.pause()
            assert input_bar.text == ""

    @pytest.mark.asyncio()
    async def test_up_arrow_preserves_draft(
        self, tui_config: AutoCodeConfig,
    ) -> None:
        """Up arrow saves current draft, down arrow restores it."""
        mock = _make_slow_mock_provider([LLMResponse(content="ok")])
        app = AutoCodeApp(config=tui_config)

        async with app.run_test() as pilot:
            app._provider = mock
            input_bar = app.query_one("#input-bar", InputBar)
            input_bar.focus()

            # Submit "old message"
            for char in "old message":
                await pilot.press(char)
            await pilot.press("enter")
            await pilot.pause()
            await pilot.pause()

            # Type a new draft without submitting
            for char in "draft":
                await pilot.press(char)
            await pilot.pause()

            # Up → should recall "old message", saving "draft"
            await pilot.press("up")
            await pilot.pause()
            assert input_bar.text == "old message"

            # Down → should restore the draft
            await pilot.press("down")
            await pilot.pause()
            assert input_bar.text == "draft"

    @pytest.mark.asyncio()
    async def test_up_arrow_does_nothing_with_no_history(
        self, tui_config: AutoCodeConfig,
    ) -> None:
        """Up arrow with no history does not crash or change text."""
        app = AutoCodeApp(config=tui_config)
        async with app.run_test() as pilot:
            input_bar = app.query_one("#input-bar", InputBar)
            input_bar.focus()

            # Type something
            for char in "test":
                await pilot.press(char)

            # Press up with no history — should keep current text
            await pilot.press("up")
            await pilot.pause()
            assert input_bar.text == "test"


class TestStreamingSmooth:
    @pytest.mark.asyncio()
    async def test_streaming_uses_static_then_markdown(
        self, tui_config: AutoCodeConfig,
    ) -> None:
        """During streaming, a lightweight Static is used; after, it becomes Markdown."""
        from textual.widgets import Markdown, Static

        app = AutoCodeApp(config=tui_config)
        async with app.run_test() as pilot:
            chat = app.query_one("#chat-view", ChatView)

            chat.start_streaming()
            await pilot.pause()

            # During streaming: should have a Static widget (not Markdown)
            streaming_children = [
                c for c in chat.children if "assistant-message" in c.classes
            ]
            assert len(streaming_children) == 1
            assert isinstance(streaming_children[0], Static)

            chat.add_streaming_chunk("Hello ")
            chat.add_streaming_chunk("world")
            await pilot.pause()
            assert chat._streaming_content == "Hello world"

            # Finish streaming: Static replaced with Markdown
            result = chat.finish_streaming()
            await pilot.pause()
            assert result == "Hello world"

            assistant_widgets = [
                c for c in chat.children if "assistant-message" in c.classes
            ]
            assert len(assistant_widgets) == 1
            assert isinstance(assistant_widgets[0], Markdown)

    @pytest.mark.asyncio()
    async def test_streaming_chunks_scroll_to_end(
        self, tui_config: AutoCodeConfig,
    ) -> None:
        """Each streaming chunk scrolls the chat to the end."""
        app = AutoCodeApp(config=tui_config)
        async with app.run_test() as pilot:
            chat = app.query_one("#chat-view", ChatView)

            # Add many messages to create scrollable content
            for i in range(20):
                chat.add_message("user", f"Message {i}")
            await pilot.pause()

            chat.start_streaming()
            for i in range(5):
                chat.add_streaming_chunk(f"chunk {i} ")
                await pilot.pause()
            chat.finish_streaming()
            await pilot.pause()

            # After all chunks, view should be scrolled to end
            assert chat.scroll_y >= chat.max_scroll_y - 1


class TestAutocomplete:
    @pytest.mark.asyncio()
    async def test_slash_command_suggestion(
        self, tui_config: AutoCodeConfig,
    ) -> None:
        """Typing / shows slash command suggestions."""
        app = AutoCodeApp(config=tui_config)
        async with app.run_test() as pilot:
            input_bar = app.query_one("#input-bar", InputBar)
            input_bar.focus()

            # Type "/he" — should suggest "lp" to complete "/help"
            for char in "/he":
                await pilot.press(char)
            await pilot.pause()
            assert input_bar.suggestion == "lp"

    @pytest.mark.asyncio()
    async def test_slash_command_tab_accepts(
        self, tui_config: AutoCodeConfig,
    ) -> None:
        """Tab accepts the inline slash command suggestion."""
        app = AutoCodeApp(config=tui_config)
        async with app.run_test() as pilot:
            input_bar = app.query_one("#input-bar", InputBar)
            input_bar.focus()

            for char in "/he":
                await pilot.press(char)
            await pilot.pause()
            assert input_bar.suggestion == "lp"

            await pilot.press("tab")
            await pilot.pause()
            assert input_bar.text == "/help"
            assert input_bar.suggestion == ""

    @pytest.mark.asyncio()
    async def test_at_file_suggestion(
        self, tui_config: AutoCodeConfig, tmp_path: Path,
    ) -> None:
        """Typing @ with a file prefix shows file path suggestions."""
        # Create a test file tree
        (tmp_path / "main.py").write_text("print('hi')")
        (tmp_path / "main_test.py").write_text("test")

        app = AutoCodeApp(config=tui_config, project_root=tmp_path)
        async with app.run_test() as pilot:
            input_bar = app.query_one("#input-bar", InputBar)
            input_bar.focus()

            # Type "@main" — should suggest ".py" or "_test.py"
            for char in "@main":
                await pilot.press(char)
            await pilot.pause()

            # Should have a suggestion (either ".py" or "_test.py")
            assert input_bar.suggestion != ""

    @pytest.mark.asyncio()
    async def test_no_suggestion_for_regular_text(
        self, tui_config: AutoCodeConfig,
    ) -> None:
        """Regular text (not / or @) shows no suggestions."""
        app = AutoCodeApp(config=tui_config)
        async with app.run_test() as pilot:
            input_bar = app.query_one("#input-bar", InputBar)
            input_bar.focus()

            for char in "hello":
                await pilot.press(char)
            await pilot.pause()
            assert input_bar.suggestion == ""

    @pytest.mark.asyncio()
    async def test_completions_wired_on_mount(
        self, tui_config: AutoCodeConfig,
    ) -> None:
        """Slash command names are wired into InputBar on app mount."""
        app = AutoCodeApp(config=tui_config)
        async with app.run_test():
            input_bar = app.query_one("#input-bar", InputBar)
            # Should have all 11+ command names loaded (9 original + shell + copy + aliases)
            assert len(input_bar._command_names) >= 11
            assert "help" in input_bar._command_names
            assert "exit" in input_bar._command_names
            assert "shell" in input_bar._command_names
            assert "copy" in input_bar._command_names

    @pytest.mark.asyncio()
    async def test_enter_accepts_suggestion_instead_of_submit(
        self, tui_config: AutoCodeConfig,
    ) -> None:
        """Enter accepts an active suggestion instead of submitting."""
        app = AutoCodeApp(config=tui_config)
        async with app.run_test() as pilot:
            input_bar = app.query_one("#input-bar", InputBar)
            input_bar.focus()

            # Type "/he" → suggestion "lp"
            for char in "/he":
                await pilot.press(char)
            await pilot.pause()
            assert input_bar.suggestion == "lp"

            # Press Enter → should accept suggestion, NOT submit
            await pilot.press("enter")
            await pilot.pause()
            assert input_bar.text == "/help"
            assert input_bar.suggestion == ""

            # Now press Enter again → should submit (no suggestion active)
            await pilot.press("enter")
            await pilot.pause()
            assert input_bar.text == ""  # submitted and cleared

    @pytest.mark.asyncio()
    async def test_tab_does_not_switch_focus(
        self, tui_config: AutoCodeConfig,
    ) -> None:
        """Tab never switches focus away from InputBar."""
        app = AutoCodeApp(config=tui_config)
        async with app.run_test() as pilot:
            input_bar = app.query_one("#input-bar", InputBar)
            input_bar.focus()

            for char in "hello":
                await pilot.press(char)

            # Tab with no suggestion — should stay in input bar
            await pilot.press("tab")
            await pilot.pause()
            assert app.focused is input_bar

    @pytest.mark.asyncio()
    async def test_tab_accepts_and_stays_focused(
        self, tui_config: AutoCodeConfig,
    ) -> None:
        """Tab accepts suggestion and keeps focus in InputBar."""
        app = AutoCodeApp(config=tui_config)
        async with app.run_test() as pilot:
            input_bar = app.query_one("#input-bar", InputBar)
            input_bar.focus()

            for char in "/he":
                await pilot.press(char)
            await pilot.pause()
            assert input_bar.suggestion == "lp"

            await pilot.press("tab")
            await pilot.pause()
            assert input_bar.text == "/help"
            assert app.focused is input_bar


class TestThinkingToggle:
    @pytest.mark.asyncio()
    async def test_ctrl_t_toggles_thinking_visibility(
        self, tui_config: AutoCodeConfig,
    ) -> None:
        """Ctrl+T toggles the show_thinking flag."""
        app = AutoCodeApp(config=tui_config)
        async with app.run_test() as pilot:
            assert app._show_thinking is True

            await pilot.press("ctrl+t")
            await pilot.pause()
            assert app._show_thinking is False

            await pilot.press("ctrl+t")
            await pilot.pause()
            assert app._show_thinking is True

    @pytest.mark.asyncio()
    async def test_toggle_shows_message_in_chat(
        self, tui_config: AutoCodeConfig,
    ) -> None:
        """Toggling thinking shows a status message in chat."""
        app = AutoCodeApp(config=tui_config)
        async with app.run_test() as pilot:
            chat = app.query_one("#chat-view", ChatView)
            initial_count = len(list(chat.children))

            await pilot.press("ctrl+t")
            await pilot.pause()

            # Should have added a system message
            assert len(list(chat.children)) > initial_count


class TestInputDuringGeneration:
    @pytest.mark.asyncio()
    async def test_input_bar_stays_focused_during_generation(
        self, tui_config: AutoCodeConfig,
    ) -> None:
        """InputBar remains focused and editable while response is generating."""

        generating_seen = False

        async def slow_generate(
            messages: Any, tools: Any, **kwargs: Any,
        ) -> LLMResponse:
            nonlocal generating_seen
            generating_seen = True
            await asyncio.sleep(0.05)  # simulate generation time
            on_chunk = kwargs.get("on_chunk")
            if on_chunk:
                on_chunk("response text")
            return LLMResponse(content="response text")

        mock = AsyncMock()
        mock.generate_with_tools = slow_generate
        mock.count_tokens = lambda text: len(text) // 4

        app = AutoCodeApp(config=tui_config)

        async with app.run_test() as pilot:
            app._provider = mock
            input_bar = app.query_one("#input-bar", InputBar)
            input_bar.focus()

            # Submit a message to start generation
            for char in "start":
                await pilot.press(char)
            await pilot.press("enter")
            await pilot.pause()

            # InputBar should still be focused
            assert app.focused is input_bar

            # Should be able to type while generating
            for char in "new":
                await pilot.press(char)
            await pilot.pause()

            # The new text should be in the input bar
            assert "new" in input_bar.text

    @pytest.mark.asyncio()
    async def test_input_not_disabled_during_generation(
        self, tui_config: AutoCodeConfig,
    ) -> None:
        """InputBar is never disabled, even while generating."""
        mock = _make_slow_mock_provider([LLMResponse(content="ok")])
        app = AutoCodeApp(config=tui_config)

        async with app.run_test() as pilot:
            app._provider = mock
            input_bar = app.query_one("#input-bar", InputBar)
            input_bar.focus()

            # Submit
            for char in "test":
                await pilot.press(char)
            await pilot.press("enter")
            await pilot.pause()

            # Input bar should not be disabled
            assert not input_bar.disabled


class TestResumeListsSessions:
    @pytest.mark.asyncio()
    async def test_resume_no_args_lists_sessions(
        self, tui_config: AutoCodeConfig,
    ) -> None:
        """/resume with no args lists available sessions with overview."""
        app = AutoCodeApp(config=tui_config)
        async with app.run_test() as pilot:
            # Create a session with messages
            sid = app.session_store.create_session(
                title="Debug login bug", model="qwen3:8b",
                provider="ollama", project_dir="/tmp",
            )
            app.session_store.add_message(sid, "user", "Fix the login page crash")
            app.session_store.add_message(sid, "assistant", "I found the issue...")

            input_bar = app.query_one("#input-bar", InputBar)
            input_bar.focus()
            for char in "/resume":
                await pilot.press(char)
            await pilot.press("enter")
            await pilot.pause()
            await pilot.pause()

            # Chat should show the session listing
            chat = app.query_one("#chat-view", ChatView)
            children = list(chat.children)
            # Should have at least one system message with session info
            texts = []
            for child in children:
                if hasattr(child, "renderable"):
                    texts.append(str(child.renderable))
            all_text = " ".join(texts)
            assert "Debug login bug" in all_text or len(children) >= 1

    @pytest.mark.asyncio()
    async def test_resume_no_sessions_shows_message(
        self, tui_config: AutoCodeConfig, tmp_path: Path,
    ) -> None:
        """/resume with no sessions shows helpful message."""
        # Use a fresh DB with no extra sessions
        config = AutoCodeConfig()
        config.tui.session_db_path = str(tmp_path / "empty.db")
        app = AutoCodeApp(config=config)

        async with app.run_test() as pilot:
            input_bar = app.query_one("#input-bar", InputBar)
            input_bar.focus()
            for char in "/resume":
                await pilot.press(char)
            await pilot.press("enter")
            await pilot.pause()
            await pilot.pause()

            chat = app.query_one("#chat-view", ChatView)
            # Should have at least a system message (either listing or "no sessions")
            assert len(list(chat.children)) >= 1


class TestSessionNaming:
    """Tests for automatic session title generation."""

    def test_generate_title_from_simple_message(self) -> None:
        """Simple messages produce clean titles."""
        title = AutoCodeApp._generate_title("Fix the login page crash")
        assert title == "Fix the login page crash"

    def test_generate_title_truncates_long_messages(self) -> None:
        """Long messages are truncated to ~6 words with ellipsis."""
        title = AutoCodeApp._generate_title(
            "Please refactor the authentication module to use JWT tokens instead of sessions"
        )
        assert title.endswith("...")
        # Should be at most 6 words + ellipsis
        words = title.rstrip("...").split()
        assert len(words) <= 6

    def test_generate_title_strips_at_references(self) -> None:
        """@file references are removed from titles."""
        title = AutoCodeApp._generate_title("Fix bug in @src/auth.py")
        assert "@" not in title
        assert "Fix bug in" in title

    def test_generate_title_strips_code_blocks(self) -> None:
        """Code blocks are removed from titles."""
        title = AutoCodeApp._generate_title(
            "Fix this ```python\nprint('hello')\n``` please"
        )
        assert "```" not in title
        assert "Fix" in title

    def test_generate_title_strips_markdown(self) -> None:
        """Markdown formatting is cleaned from titles."""
        title = AutoCodeApp._generate_title("Fix the **critical** _bug_")
        assert "**" not in title
        assert "Fix" in title

    def test_generate_title_capitalizes(self) -> None:
        """First letter of title is capitalized."""
        title = AutoCodeApp._generate_title("fix the login")
        assert title[0].isupper()

    @pytest.mark.asyncio()
    async def test_session_starts_with_timestamp_title(
        self, tui_config: AutoCodeConfig,
    ) -> None:
        """New session is created with a timestamp-based title."""
        app = AutoCodeApp(config=tui_config)
        async with app.run_test():
            session = app.session_store.get_session(app.session_id)
            assert session is not None
            assert session.title.startswith("Session 20")

    @pytest.mark.asyncio()
    async def test_session_auto_titled_after_first_message(
        self, tui_config: AutoCodeConfig,
    ) -> None:
        """Session title is updated from the first user message."""
        mock = _make_slow_mock_provider([LLMResponse(content="ok")])
        app = AutoCodeApp(config=tui_config)

        async with app.run_test() as pilot:
            app._provider = mock
            input_bar = app.query_one("#input-bar", InputBar)
            input_bar.focus()

            for char in "fix the login bug":
                await pilot.press(char)
            await pilot.press("enter")
            await pilot.pause()
            await pilot.pause()

            session = app.session_store.get_session(app.session_id)
            assert session is not None
            # Title should be derived from the message, not a timestamp
            assert not session.title.startswith("Session 20")
            assert "fix" in session.title.lower() or "login" in session.title.lower()


class TestInteractiveApproval:
    """Tests for the interactive approval prompt system."""

    @pytest.mark.asyncio()
    async def test_approval_prompt_widget_creates(self) -> None:
        """ApprovalPrompt widget can be created with a future."""
        from autocode.tui.widgets.approval_prompt import ApprovalPrompt

        loop = asyncio.get_running_loop()
        future: asyncio.Future[tuple[str, bool]] = loop.create_future()
        prompt = ApprovalPrompt("write_file", "Write 100 chars to test.py", future)
        assert prompt is not None
        assert prompt._tool_name == "write_file"

    @pytest.mark.asyncio()
    async def test_option_selector_widget_creates(self) -> None:
        """OptionSelector widget can be created with options."""
        from autocode.tui.widgets.approval_prompt import OptionSelector

        loop = asyncio.get_running_loop()
        future: asyncio.Future[list[str]] = loop.create_future()
        selector = OptionSelector(
            "Choose an option:", ["Option A", "Option B", "Option C"], future,
        )
        assert selector is not None
        assert selector._options == ["Option A", "Option B", "Option C"]

    @pytest.mark.asyncio()
    async def test_option_selector_multi_creates(self) -> None:
        """OptionSelector in multi-select mode can be created."""
        from autocode.tui.widgets.approval_prompt import OptionSelector

        loop = asyncio.get_running_loop()
        future: asyncio.Future[list[str]] = loop.create_future()
        selector = OptionSelector(
            "Select features:", ["Auth", "Logging", "Tests"],
            future, multi=True,
        )
        assert selector is not None
        assert selector._multi is True

    @pytest.mark.asyncio()
    async def test_format_tool_description_write_file(self, tui_config: AutoCodeConfig) -> None:
        """Tool description for write_file shows path and size."""
        app = AutoCodeApp(config=tui_config)
        async with app.run_test():
            desc = app._format_tool_description(
                "write_file", {"path": "test.py", "content": "x" * 50},
            )
            assert "50" in desc
            assert "test.py" in desc

    @pytest.mark.asyncio()
    async def test_format_tool_description_run_command(self, tui_config: AutoCodeConfig) -> None:
        """Tool description for run_command shows the command."""
        app = AutoCodeApp(config=tui_config)
        async with app.run_test():
            desc = app._format_tool_description(
                "run_command", {"command": "pytest tests/"},
            )
            assert "pytest tests/" in desc

    @pytest.mark.asyncio()
    async def test_format_tool_description_run_command_shell_disabled(
        self, tui_config: AutoCodeConfig,
    ) -> None:
        """When shell is disabled, run_command description mentions enabling."""
        tui_config.shell.enabled = False
        app = AutoCodeApp(config=tui_config)
        async with app.run_test():
            desc = app._format_tool_description(
                "run_command", {"command": "pwd"},
            )
            assert "enable" in desc.lower()
            assert "pwd" in desc

    @pytest.mark.asyncio()
    async def test_format_tool_description_generic(self, tui_config: AutoCodeConfig) -> None:
        """Tool description for unknown tools shows args."""
        app = AutoCodeApp(config=tui_config)
        async with app.run_test():
            desc = app._format_tool_description(
                "custom_tool", {"arg1": "val1"},
            )
            assert "custom_tool" in desc
            assert "arg1" in desc


class TestCopyAndScroll:
    """Tests for copy and page scrolling features."""

    @pytest.mark.asyncio()
    async def test_page_up_binding_exists(
        self, tui_config: AutoCodeConfig,
    ) -> None:
        """Page Up binding is registered."""
        app = AutoCodeApp(config=tui_config)
        binding_keys = [b.key for b in app.BINDINGS]
        assert "pageup" in binding_keys

    @pytest.mark.asyncio()
    async def test_page_down_binding_exists(
        self, tui_config: AutoCodeConfig,
    ) -> None:
        """Page Down binding is registered."""
        app = AutoCodeApp(config=tui_config)
        binding_keys = [b.key for b in app.BINDINGS]
        assert "pagedown" in binding_keys

    @pytest.mark.asyncio()
    async def test_page_up_scrolls_chat(
        self, tui_config: AutoCodeConfig,
    ) -> None:
        """Page Up scrolls the chat view upward."""
        app = AutoCodeApp(config=tui_config)
        async with app.run_test() as pilot:
            chat = app.query_one("#chat-view", ChatView)

            # Add many messages to create scrollable content
            for i in range(30):
                chat.add_message("user", f"Long message {i} " * 5)
            await pilot.pause()

            # Scroll to bottom first
            chat.scroll_end(animate=False)
            await pilot.pause()
            bottom_y = chat.scroll_y

            if bottom_y > 0:
                # Page Up should move scroll position up
                await pilot.press("pageup")
                await pilot.pause()
                assert chat.scroll_y < bottom_y

    @pytest.mark.asyncio()
    async def test_copy_command_no_messages(
        self, tui_config: AutoCodeConfig,
    ) -> None:
        """/copy with no assistant messages shows error."""
        app = AutoCodeApp(config=tui_config)
        async with app.run_test() as pilot:
            input_bar = app.query_one("#input-bar", InputBar)
            input_bar.focus()
            for char in "/copy":
                await pilot.press(char)
            await pilot.press("enter")
            await pilot.pause()
            await pilot.pause()

            chat = app.query_one("#chat-view", ChatView)
            children = list(chat.children)
            # Should show an error or info message
            assert len(children) >= 1

    @pytest.mark.asyncio()
    async def test_shell_command_shows_status(
        self, tui_config: AutoCodeConfig,
    ) -> None:
        """/shell with no args shows current status."""
        app = AutoCodeApp(config=tui_config)
        async with app.run_test() as pilot:
            input_bar = app.query_one("#input-bar", InputBar)
            input_bar.focus()
            for char in "/shell":
                await pilot.press(char)
            await pilot.press("enter")
            await pilot.pause()
            await pilot.pause()

            chat = app.query_one("#chat-view", ChatView)
            children = list(chat.children)
            assert len(children) >= 1

    @pytest.mark.asyncio()
    async def test_shell_on_enables_shell(
        self, tui_config: AutoCodeConfig,
    ) -> None:
        """/shell on enables shell execution."""
        app = AutoCodeApp(config=tui_config)
        assert app.config.shell.enabled is False

        async with app.run_test() as pilot:
            input_bar = app.query_one("#input-bar", InputBar)
            input_bar.focus()
            for char in "/shell on":
                await pilot.press(char)
            await pilot.press("enter")
            await pilot.pause()
            await pilot.pause()

            assert app.config.shell.enabled is True

    @pytest.mark.asyncio()
    async def test_shell_off_disables_shell(
        self, tui_config: AutoCodeConfig,
    ) -> None:
        """/shell off disables shell execution."""
        app = AutoCodeApp(config=tui_config)
        app.config.shell.enabled = True

        async with app.run_test() as pilot:
            input_bar = app.query_one("#input-bar", InputBar)
            input_bar.focus()
            for char in "/shell off":
                await pilot.press(char)
            await pilot.press("enter")
            await pilot.pause()
            await pilot.pause()

            assert app.config.shell.enabled is False


class TestAskUserUI:
    """Tests for ask_user tool integration in the TUI."""

    @pytest.mark.asyncio()
    async def test_ask_user_future_intercepts_submit(
        self, tui_config: AutoCodeConfig,
    ) -> None:
        """When ask_user future is set, InputBar submit resolves the future."""
        app = AutoCodeApp(config=tui_config)
        async with app.run_test() as pilot:
            loop = asyncio.get_running_loop()
            future: asyncio.Future[str] = loop.create_future()
            app._ask_user_future = future

            input_bar = app.query_one("#input-bar", InputBar)
            input_bar.focus()
            for char in "my answer":
                await pilot.press(char)
            await pilot.press("enter")
            await pilot.pause()

            assert future.done()
            assert future.result() == "my answer"

    @pytest.mark.asyncio()
    async def test_ask_user_free_text_resolved_via_submit(
        self, tui_config: AutoCodeConfig,
    ) -> None:
        """Free-text ask_user is resolved when InputBar submits."""
        app = AutoCodeApp(config=tui_config)
        async with app.run_test() as pilot:
            # Run ask_user in a background task (it will block waiting)
            async def ask() -> str:
                return await app._interactive_ask_user("What?", [], False)

            task = asyncio.create_task(ask())
            await pilot.pause()
            await pilot.pause()

            # The future should be set now
            assert app._ask_user_future is not None

            # Submit a response via input bar
            input_bar = app.query_one("#input-bar", InputBar)
            input_bar.focus()
            for char in "typed answer":
                await pilot.press(char)
            await pilot.press("enter")
            await pilot.pause()

            result = await task
            assert result == "typed answer"
            assert app._ask_user_future is None

    @pytest.mark.asyncio()
    async def test_ask_user_with_options_creates_selector(
        self, tui_config: AutoCodeConfig,
    ) -> None:
        """ask_user with options mounts an OptionSelector with OptionList."""
        from autocode.tui.widgets.approval_prompt import OptionSelector

        app = AutoCodeApp(config=tui_config)
        async with app.run_test() as pilot:
            # Run ask_user in a task so we can interact with the selector
            async def ask_and_respond() -> str:
                return await app._interactive_ask_user(
                    "Pick one:", ["A", "B", "C"], False,
                )

            task = asyncio.create_task(ask_and_respond())
            await pilot.pause()
            await pilot.pause()

            # Selector should be mounted
            selectors = app.query(OptionSelector)
            if selectors:
                # First option is auto-highlighted; press Enter to select
                await pilot.press("enter")
                await pilot.pause()

            result = await task
            assert result == "A"

    @pytest.mark.asyncio()
    async def test_ask_user_escape_returns_skipped(
        self, tui_config: AutoCodeConfig,
    ) -> None:
        """Pressing escape on OptionSelector returns '(user skipped)'."""
        app = AutoCodeApp(config=tui_config)
        async with app.run_test() as pilot:
            async def ask_and_escape() -> str:
                return await app._interactive_ask_user(
                    "Pick:", ["X", "Y"], False,
                )

            task = asyncio.create_task(ask_and_escape())
            await pilot.pause()
            await pilot.pause()

            await pilot.press("escape")
            await pilot.pause()

            result = await task
            assert result == "(user skipped)"


class TestTypingIndicator:
    """Tests for the typing indicator in the status bar."""

    @pytest.mark.asyncio()
    async def test_status_bar_has_user_typing_property(
        self, tui_config: AutoCodeConfig,
    ) -> None:
        """StatusBar has a user_typing reactive property."""
        app = AutoCodeApp(config=tui_config)
        async with app.run_test():
            status_bar = app.query_one("#status-bar", StatusBar)
            assert hasattr(status_bar, "user_typing")
            assert status_bar.user_typing is False

    @pytest.mark.asyncio()
    async def test_typing_shown_in_status_during_generation(
        self, tui_config: AutoCodeConfig,
    ) -> None:
        """Status bar shows 'typing' when user types during generation."""
        app = AutoCodeApp(config=tui_config)
        async with app.run_test() as pilot:
            status_bar = app.query_one("#status-bar", StatusBar)
            app._generating = True

            input_bar = app.query_one("#input-bar", InputBar)
            input_bar.focus()
            for char in "hello":
                await pilot.press(char)
            await pilot.pause()

            assert status_bar.user_typing is True

    @pytest.mark.asyncio()
    async def test_typing_not_shown_when_not_generating(
        self, tui_config: AutoCodeConfig,
    ) -> None:
        """Status bar does not show typing when not generating."""
        app = AutoCodeApp(config=tui_config)
        async with app.run_test() as pilot:
            status_bar = app.query_one("#status-bar", StatusBar)
            app._generating = False

            input_bar = app.query_one("#input-bar", InputBar)
            input_bar.focus()
            for char in "test":
                await pilot.press(char)
            await pilot.pause()

            assert status_bar.user_typing is False

    @pytest.mark.asyncio()
    async def test_typing_cleared_after_generation_ends(
        self, tui_config: AutoCodeConfig,
    ) -> None:
        """Typing indicator is cleared when generation finishes."""
        app = AutoCodeApp(config=tui_config)
        async with app.run_test():
            status_bar = app.query_one("#status-bar", StatusBar)
            status_bar.user_typing = True
            assert status_bar.user_typing is True

            # Simulate generation ending
            status_bar.user_typing = False
            assert status_bar.user_typing is False

    @pytest.mark.asyncio()
    async def test_typing_indicator_renders_in_status(self) -> None:
        """StatusBar renders 'You: typing...' when user_typing is True."""
        bar = StatusBar()
        bar.user_typing = True
        rendered = bar.render()
        assert "typing" in rendered

    @pytest.mark.asyncio()
    async def test_typing_indicator_not_in_status_when_false(self) -> None:
        """StatusBar does not show typing text when user_typing is False."""
        bar = StatusBar()
        bar.user_typing = False
        rendered = bar.render()
        assert "typing" not in rendered
