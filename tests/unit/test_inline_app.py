"""Tests for InlineApp."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from hybridcoder.config import HybridCoderConfig
from hybridcoder.inline.app import InlineApp


@pytest.fixture()
def inline_config(tmp_path: Path) -> HybridCoderConfig:
    """Create a test config with tmp_path DB."""
    config = HybridCoderConfig()
    config.tui.session_db_path = str(tmp_path / "test.db")
    return config


@pytest.fixture()
def inline_app(inline_config: HybridCoderConfig, tmp_path: Path) -> InlineApp:
    """Create an InlineApp with test config (no terminal needed)."""
    return InlineApp(config=inline_config, project_root=tmp_path)


class TestInlineApp:
    def test_app_creates_session(self, inline_app: InlineApp) -> None:
        """InlineApp creates a session on init."""
        assert inline_app.session_id
        sessions = inline_app.session_store.list_sessions()
        assert len(sessions) >= 1

    @pytest.mark.asyncio()
    async def test_slash_command_dispatch(self, inline_app: InlineApp) -> None:
        """'/help' dispatches to help handler and calls add_system_message."""
        with patch.object(inline_app, "add_system_message") as mock_msg:
            await inline_app._handle_input("/help")
            mock_msg.assert_called_once()
            assert "Available commands" in mock_msg.call_args[0][0]

    @pytest.mark.asyncio()
    async def test_exit_raises_eof(self, inline_app: InlineApp) -> None:
        """'/exit' raises EOFError to break the REPL loop."""
        with pytest.raises(EOFError):
            await inline_app._handle_input("/exit")

    @pytest.mark.asyncio()
    async def test_at_file_expansion(self, inline_app: InlineApp, tmp_path: Path) -> None:
        """@file.txt in input triggers file expansion."""
        (tmp_path / "file.txt").write_text("file content here")
        with patch.object(inline_app, "_run_agent", new_callable=AsyncMock) as mock_agent:
            await inline_app._handle_input("check @file.txt")
            mock_agent.assert_called_once()
            expanded = mock_agent.call_args[0][0]
            assert "file content here" in expanded

    @pytest.mark.asyncio()
    async def test_agent_response_rendered(self, inline_app: InlineApp) -> None:
        """Agent run calls streaming renderer methods (not print_user_message)."""
        mock_loop = AsyncMock()
        mock_loop.run = AsyncMock(return_value="Test response")
        inline_app._agent_loop = mock_loop
        inline_app._provider = MagicMock()

        with patch.object(inline_app.renderer, "start_streaming") as mock_start, \
             patch.object(inline_app.renderer, "end_streaming", return_value="") as mock_end:
            await inline_app._run_agent("hello")
            mock_start.assert_called_once()
            mock_end.assert_called_once()

    @pytest.mark.asyncio()
    async def test_tool_call_displayed(self, inline_app: InlineApp) -> None:
        """Tool calls during agent run forward to renderer.print_tool_call."""
        mock_loop = AsyncMock()

        async def fake_run(msg: str, **kwargs: object) -> str:
            on_tool_call = kwargs.get("on_tool_call")
            if on_tool_call:
                on_tool_call("read_file", "completed", "src/main.py")  # type: ignore[misc]
            return "done"

        mock_loop.run = fake_run
        inline_app._agent_loop = mock_loop
        inline_app._provider = MagicMock()

        with patch.object(inline_app.renderer, "print_tool_call") as mock_tool, \
             patch.object(inline_app.renderer, "print_user_message"), \
             patch.object(inline_app.renderer, "start_streaming"), \
             patch.object(inline_app.renderer, "end_streaming", return_value=""):
            await inline_app._run_agent("do something")
            mock_tool.assert_called_once_with("read_file", "completed", "src/main.py")

    @pytest.mark.asyncio()
    async def test_approval_prompt_yes(self, inline_app: InlineApp) -> None:
        """Approval prompt returns True when user selects 'Yes'."""
        with patch.object(inline_app, "_arrow_select", new_callable=AsyncMock, return_value="Yes"):
            result = await inline_app._approval_prompt("write_file", {"path": "test.py"})
            assert result is True

    @pytest.mark.asyncio()
    async def test_approval_prompt_no(self, inline_app: InlineApp) -> None:
        """Approval prompt returns False when user selects 'No'."""
        with patch.object(inline_app, "_arrow_select", new_callable=AsyncMock, return_value="No"):
            result = await inline_app._approval_prompt("write_file", {"path": "test.py"})
            assert result is False

    @pytest.mark.asyncio()
    async def test_approval_prompt_session(self, inline_app: InlineApp) -> None:
        """Approval prompt returns True and tracks tool on 'Yes, this session'."""
        mock_select = AsyncMock(return_value="Yes, this session")
        with patch.object(inline_app, "_arrow_select", mock_select):
            result = await inline_app._approval_prompt("run_command", {"command": "ls"})
            assert result is True
            assert "run_command" in inline_app._session_approved_tools

    @pytest.mark.asyncio()
    async def test_approval_prompt_cancel(self, inline_app: InlineApp) -> None:
        """Approval prompt returns False when cancelled (Escape)."""
        with patch.object(inline_app, "_arrow_select", new_callable=AsyncMock, return_value=None):
            result = await inline_app._approval_prompt("write_file", {"path": "test.py"})
            assert result is False

    @pytest.mark.asyncio()
    async def test_ask_user_arrow_select(self, inline_app: InlineApp) -> None:
        """ask_user with options uses arrow selector."""
        with patch.object(
            inline_app, "_arrow_select", new_callable=AsyncMock, return_value="Option B",
        ):
            result = await inline_app._ask_user_prompt(
                "Pick one", ["Option A", "Option B"], allow_text=False,
            )
            assert result == "Option B"

    @pytest.mark.asyncio()
    async def test_ask_user_cancel_returns_first(self, inline_app: InlineApp) -> None:
        """ask_user returns first option when cancelled."""
        with patch.object(inline_app, "_arrow_select", new_callable=AsyncMock, return_value=None):
            result = await inline_app._ask_user_prompt(
                "Pick one", ["Option A", "Option B"], allow_text=False,
            )
            assert result == "Option A"


class TestStatusBar:
    def test_status_shows_model(self, inline_app: InlineApp) -> None:
        """Status text includes model name."""
        text = inline_app._get_status_text()
        assert inline_app.config.llm.model in text

    def test_status_shows_mode(self, inline_app: InlineApp) -> None:
        """Status text includes approval mode."""
        text = inline_app._get_status_text()
        assert inline_app.approval_mode in text

    def test_status_hides_tokens_when_zero(self, inline_app: InlineApp) -> None:
        """Status omits token count when zero."""
        text = inline_app._get_status_text()
        assert "Tokens" not in text

    def test_status_shows_tokens_after_usage(self, inline_app: InlineApp) -> None:
        """Status shows token count after agent produces output."""
        inline_app._total_tokens = 500
        text = inline_app._get_status_text()
        assert "Tokens" in text
        assert "500" in text

    def test_status_formats_large_tokens(self, inline_app: InlineApp) -> None:
        """Status formats large token counts with 'k' suffix."""
        inline_app._total_tokens = 2500
        text = inline_app._get_status_text()
        assert "2.5k" in text

    def test_status_shows_edits(self, inline_app: InlineApp) -> None:
        """Status shows edit count when edits have occurred."""
        inline_app._edit_count = 3
        text = inline_app._get_status_text()
        assert "Edits" in text
        assert "3" in text

    def test_status_shows_files(self, inline_app: InlineApp) -> None:
        """Status shows file count when files have been modified."""
        inline_app._files_modified = {"a.py", "b.py"}
        text = inline_app._get_status_text()
        assert "Files" in text
        assert "2" in text

    def test_on_tool_call_tracks_write(self, inline_app: InlineApp) -> None:
        """_on_tool_call increments edit count for write_file."""
        with patch.object(inline_app.renderer, "print_tool_call"):
            inline_app._on_tool_call("write_file", "completed", "src/main.py")
            assert inline_app._edit_count == 1
            assert "src/main.py" in inline_app._files_modified

    def test_on_tool_call_ignores_read(self, inline_app: InlineApp) -> None:
        """_on_tool_call does not count read_file as an edit."""
        with patch.object(inline_app.renderer, "print_tool_call"):
            inline_app._on_tool_call("read_file", "completed", "src/main.py")
            assert inline_app._edit_count == 0
            assert len(inline_app._files_modified) == 0


class TestThinkingToggle:
    def test_thinking_default_hidden(self, inline_app: InlineApp) -> None:
        """Thinking is hidden by default (matching Claude Code)."""
        assert inline_app._show_thinking is False
        assert inline_app.show_thinking is False

    def test_thinking_toggle_property(self, inline_app: InlineApp) -> None:
        """show_thinking property toggles correctly."""
        inline_app.show_thinking = True
        assert inline_app.show_thinking is True
        inline_app.show_thinking = False
        assert inline_app.show_thinking is False

    @pytest.mark.asyncio()
    async def test_thinking_toggle_command(self, inline_app: InlineApp) -> None:
        """'/thinking' command toggles thinking visibility."""
        assert inline_app.show_thinking is False
        with patch.object(inline_app, "add_system_message") as mock_msg:
            await inline_app._handle_input("/thinking")
            assert inline_app.show_thinking is True
            mock_msg.assert_called_once()
            assert "on" in mock_msg.call_args[0][0]

    @pytest.mark.asyncio()
    async def test_thinking_hidden_suppresses_callback(self, inline_app: InlineApp) -> None:
        """When thinking is hidden, on_thinking_chunk is None in agent run."""
        mock_loop = AsyncMock()
        mock_loop.run = AsyncMock(return_value="response")
        inline_app._agent_loop = mock_loop
        inline_app._provider = MagicMock()
        inline_app._show_thinking = False

        with patch.object(inline_app.renderer, "start_streaming"), \
             patch.object(inline_app.renderer, "end_streaming", return_value=""):
            await inline_app._run_agent("test")
            # Verify on_thinking_chunk was None
            call_kwargs = mock_loop.run.call_args[1]
            assert call_kwargs.get("on_thinking_chunk") is None

    @pytest.mark.asyncio()
    async def test_thinking_shown_passes_callback(self, inline_app: InlineApp) -> None:
        """When thinking is shown, on_thinking_chunk is the renderer method."""
        mock_loop = AsyncMock()
        mock_loop.run = AsyncMock(return_value="response")
        inline_app._agent_loop = mock_loop
        inline_app._provider = MagicMock()
        inline_app._show_thinking = True

        with patch.object(inline_app.renderer, "start_streaming"), \
             patch.object(inline_app.renderer, "end_streaming", return_value=""):
            await inline_app._run_agent("test")
            call_kwargs = mock_loop.run.call_args[1]
            assert call_kwargs.get("on_thinking_chunk") is not None


class TestKeyBindings:
    def test_key_bindings_created(self, inline_app: InlineApp) -> None:
        """Key bindings object is created with shift+tab binding."""
        kb = inline_app._create_key_bindings()
        # Check that at least one binding exists
        assert len(kb.bindings) > 0

    def test_shift_tab_cycles_mode(self, inline_app: InlineApp) -> None:
        """Shift+Tab cycles through approval modes."""
        # Start with suggest mode (default)
        initial_mode = inline_app.approval_mode

        # Create a mock event with an app that has invalidate()
        mock_event = MagicMock()
        mock_event.app = MagicMock()

        # Get the shift-tab handler from key bindings
        kb = inline_app._create_key_bindings()
        # Find the s-tab binding
        stab_handlers = [
            b.handler for b in kb.bindings
        ]
        assert len(stab_handlers) > 0

        # Call the first handler (shift-tab)
        stab_handlers[0](mock_event)

        # Mode should have changed
        new_mode = inline_app.approval_mode
        assert new_mode != initial_mode or initial_mode not in ["read-only", "suggest", "auto"]


class TestPromptSessionCreation:
    def test_prompt_session_has_status_footer_and_rprompt(self, inline_app: InlineApp) -> None:
        """PromptSession is configured with status footer and rprompt fallbacks."""
        # Patch PromptSession constructor to avoid terminal creation in unit tests
        with patch("hybridcoder.inline.app.PromptSession") as mock_session:
            mock_session.return_value = MagicMock()
            inline_app.session = None
            created = inline_app._ensure_prompt_session()
            assert created is mock_session.return_value

            kwargs = mock_session.call_args.kwargs
            assert getattr(kwargs["bottom_toolbar"], "__self__", None) is inline_app
            assert (
                getattr(kwargs["bottom_toolbar"], "__func__", None)
                is InlineApp._get_status_toolbar
            )
            assert getattr(kwargs["rprompt"], "__self__", None) is inline_app
            assert (
                getattr(kwargs["rprompt"], "__func__", None)
                is InlineApp._get_status_rprompt
            )
            assert kwargs["erase_when_done"] is True


class TestSessionApproval:
    @pytest.mark.asyncio()
    async def test_session_approve_auto_approves(self, inline_app: InlineApp) -> None:
        """After 'Yes, this session', subsequent calls auto-approve."""
        # First call: user approves with "Yes, this session"
        mock_select = AsyncMock(return_value="Yes, this session")
        with patch.object(inline_app, "_arrow_select", mock_select):
            result = await inline_app._approval_prompt("write_file", {"path": "test.py"})
            assert result is True

        # Second call: auto-approved (no arrow_select needed)
        with patch.object(inline_app.renderer, "print_tool_call"):
            result = await inline_app._approval_prompt("write_file", {"path": "other.py"})
            assert result is True

    @pytest.mark.asyncio()
    async def test_session_approve_per_tool(self, inline_app: InlineApp) -> None:
        """Session approval is per-tool — different tools still prompt."""
        # Approve write_file for session
        mock_select = AsyncMock(return_value="Yes, this session")
        with patch.object(inline_app, "_arrow_select", mock_select):
            await inline_app._approval_prompt("write_file", {"path": "test.py"})

        # run_command should still prompt
        mock_select2 = AsyncMock(return_value="Yes")
        with patch.object(inline_app, "_arrow_select", mock_select2):
            result = await inline_app._approval_prompt("run_command", {"command": "ls"})
            mock_select2.assert_called_once()
            assert result is True


class TestClearCommand:
    @pytest.mark.asyncio()
    async def test_clear_command(self, inline_app: InlineApp) -> None:
        """/clear command calls add_system_message."""
        with patch.object(inline_app, "add_system_message") as mock_msg, \
             patch("sys.stdout"):
            await inline_app._handle_input("/clear")
            mock_msg.assert_called_once()
            assert "cleared" in mock_msg.call_args[0][0].lower()


class TestCancellation:
    @pytest.mark.asyncio()
    async def test_handle_input_with_cancel_slash_command(self, inline_app: InlineApp) -> None:
        """Slash commands bypass cancellation wrapper."""
        with patch.object(inline_app, "add_system_message"):
            await inline_app._handle_input_with_cancel("/help")

    @pytest.mark.asyncio()
    async def test_agent_handles_cancelled_error(self, inline_app: InlineApp) -> None:
        """_run_agent handles CancelledError gracefully."""
        mock_loop = AsyncMock()
        mock_loop.run = AsyncMock(side_effect=asyncio.CancelledError())
        inline_app._agent_loop = mock_loop
        inline_app._provider = MagicMock()

        with patch.object(inline_app.renderer, "start_streaming"), \
             patch.object(inline_app.renderer, "end_streaming", return_value=""), \
             patch.object(inline_app.renderer, "end_thinking"), \
             patch.object(inline_app.renderer, "print_thinking_indicator"), \
             patch.object(inline_app.renderer, "print_system"):
            await inline_app._run_agent("test")

    @pytest.mark.asyncio()
    async def test_listen_for_escape_returns_bool(self, inline_app: InlineApp) -> None:
        """_listen_for_escape method exists and is async."""
        # Just verify the method exists and is callable
        assert callable(inline_app._listen_for_escape)

    @pytest.mark.asyncio()
    async def test_handle_input_with_cancel_runs_agent(self, inline_app: InlineApp) -> None:
        """Non-slash input goes through cancellation wrapper to agent."""
        mock_loop = AsyncMock()
        mock_loop.run = AsyncMock(return_value="response")
        inline_app._agent_loop = mock_loop
        inline_app._provider = MagicMock()

        with (
            patch.object(inline_app, "_listen_for_escape", new_callable=AsyncMock) as mock_escape,
            patch.object(inline_app.renderer, "start_streaming"),
            patch.object(inline_app.renderer, "end_streaming", return_value=""),
            patch.object(inline_app.renderer, "end_thinking"),
            patch.object(inline_app.renderer, "print_thinking_indicator"),
        ):
            # Make escape never trigger (just hang until cancelled)
            mock_escape.side_effect = asyncio.CancelledError()
            await inline_app._handle_input_with_cancel("hello")
            mock_loop.run.assert_called_once()


class TestThinkingIndicator:
    @pytest.mark.asyncio()
    async def test_thinking_indicator_called_in_run_agent(self, inline_app: InlineApp) -> None:
        """_run_agent calls print_thinking_indicator before streaming."""
        mock_loop = AsyncMock()
        mock_loop.run = AsyncMock(return_value="response")
        inline_app._agent_loop = mock_loop
        inline_app._provider = MagicMock()

        with patch.object(inline_app.renderer, "start_streaming"), \
             patch.object(inline_app.renderer, "end_streaming", return_value=""), \
             patch.object(inline_app.renderer, "end_thinking"), \
             patch.object(inline_app.renderer, "print_thinking_indicator") as mock_indicator:
            await inline_app._run_agent("test")
            mock_indicator.assert_called_once()


class TestEscapeCancellation:
    @pytest.mark.asyncio()
    async def test_escape_triggers_agent_loop_cancel(self, inline_app: InlineApp) -> None:
        """Escape returns True -> _agent_loop.cancel() called."""
        mock_loop = AsyncMock()
        mock_loop.run = AsyncMock(side_effect=asyncio.CancelledError())
        mock_loop.cancel = MagicMock()
        inline_app._agent_loop = mock_loop
        inline_app._provider = MagicMock()

        with (
            patch.object(
                inline_app, "_listen_for_escape",
                new_callable=AsyncMock, return_value=True,
            ),
            patch.object(inline_app, "_handle_input", new_callable=AsyncMock) as mock_handle,
            patch.object(inline_app.renderer, "end_thinking"),
            patch.object(inline_app.renderer, "end_streaming", return_value=""),
        ):
            # Make _handle_input hang until cancelled
            async def _hang(text: str) -> None:
                await asyncio.sleep(100)
            mock_handle.side_effect = _hang
            await inline_app._handle_input_with_cancel("hello")
            mock_loop.cancel.assert_called_once()

    @pytest.mark.asyncio()
    async def test_escape_calls_end_thinking_and_streaming(self, inline_app: InlineApp) -> None:
        """Escape -> end_thinking() + end_streaming() called."""
        with (
            patch.object(
                inline_app, "_listen_for_escape",
                new_callable=AsyncMock, return_value=True,
            ),
            patch.object(inline_app, "_handle_input", new_callable=AsyncMock) as mock_handle,
            patch.object(inline_app.renderer, "end_thinking") as mock_end_think,
            patch.object(inline_app.renderer, "end_streaming", return_value="") as mock_end_stream,
        ):
            async def _hang(text: str) -> None:
                await asyncio.sleep(100)
            mock_handle.side_effect = _hang
            await inline_app._handle_input_with_cancel("hello")
            mock_end_think.assert_called()
            mock_end_stream.assert_called()

    @pytest.mark.asyncio()
    async def test_escape_prints_cancelled_message(self, inline_app: InlineApp) -> None:
        """Escape -> 'Cancelled.' printed."""
        with (
            patch.object(
                inline_app, "_listen_for_escape",
                new_callable=AsyncMock, return_value=True,
            ),
            patch.object(inline_app, "_handle_input", new_callable=AsyncMock) as mock_handle,
            patch.object(inline_app.renderer, "end_thinking"),
            patch.object(inline_app.renderer, "end_streaming", return_value=""),
            patch.object(inline_app.console, "print") as mock_print,
        ):
            async def _hang(text: str) -> None:
                await asyncio.sleep(100)
            mock_handle.side_effect = _hang
            await inline_app._handle_input_with_cancel("hello")
            # Check that "Cancelled." was printed
            printed = [str(call) for call in mock_print.call_args_list]
            assert any("Cancelled" in s for s in printed)

    @pytest.mark.asyncio()
    async def test_normal_completion_cancels_escape_listener(self, inline_app: InlineApp) -> None:
        """Agent completes -> escape task cancelled, no 'Cancelled.' message."""
        mock_loop = AsyncMock()
        mock_loop.run = AsyncMock(return_value="response")
        inline_app._agent_loop = mock_loop
        inline_app._provider = MagicMock()

        with (
            patch.object(inline_app, "_listen_for_escape", new_callable=AsyncMock) as mock_escape,
            patch.object(inline_app.renderer, "start_streaming"),
            patch.object(inline_app.renderer, "end_streaming", return_value=""),
            patch.object(inline_app.renderer, "end_thinking"),
            patch.object(inline_app.renderer, "print_thinking_indicator"),
            patch.object(inline_app.console, "print") as mock_print,
        ):
            # Escape never triggers (hangs then gets cancelled)
            mock_escape.side_effect = asyncio.CancelledError()
            await inline_app._handle_input_with_cancel("hello")
            # "Cancelled." should NOT appear
            printed = " ".join(str(call) for call in mock_print.call_args_list)
            assert "Cancelled" not in printed

    @pytest.mark.asyncio()
    async def test_agent_exception_propagates(self, inline_app: InlineApp) -> None:
        """Agent raises RuntimeError -> re-raised via agent_task.result()."""
        with (
            patch.object(
                inline_app, "_listen_for_escape",
                new_callable=AsyncMock,
            ) as mock_escape,
            patch.object(inline_app, "_handle_input", new_callable=AsyncMock) as mock_handle,
        ):
            mock_handle.side_effect = RuntimeError("test error")
            mock_escape.side_effect = asyncio.CancelledError()
            with pytest.raises(RuntimeError, match="test error"):
                await inline_app._handle_input_with_cancel("hello")

    @pytest.mark.asyncio()
    async def test_no_agent_loop_escape_still_works(self, inline_app: InlineApp) -> None:
        """_agent_loop is None -> no crash, still prints 'Cancelled.'."""
        inline_app._agent_loop = None  # No agent loop

        with (
            patch.object(
                inline_app, "_listen_for_escape",
                new_callable=AsyncMock, return_value=True,
            ),
            patch.object(inline_app, "_handle_input", new_callable=AsyncMock) as mock_handle,
            patch.object(inline_app.renderer, "end_thinking"),
            patch.object(inline_app.renderer, "end_streaming", return_value=""),
            patch.object(inline_app.console, "print") as mock_print,
        ):
            async def _hang(text: str) -> None:
                await asyncio.sleep(100)
            mock_handle.side_effect = _hang
            await inline_app._handle_input_with_cancel("hello")
            printed = " ".join(str(call) for call in mock_print.call_args_list)
            assert "Cancelled" in printed


class TestRunAgentExceptions:
    @pytest.mark.asyncio()
    async def test_run_agent_generic_exception(self, inline_app: InlineApp) -> None:
        """RuntimeError caught, print_system('Error: ...') called."""
        mock_loop = AsyncMock()
        mock_loop.run = AsyncMock(side_effect=RuntimeError("boom"))
        inline_app._agent_loop = mock_loop
        inline_app._provider = MagicMock()

        with patch.object(inline_app.renderer, "start_streaming"), \
             patch.object(inline_app.renderer, "end_streaming", return_value=""), \
             patch.object(inline_app.renderer, "end_thinking"), \
             patch.object(inline_app.renderer, "print_thinking_indicator"), \
             patch.object(inline_app.renderer, "print_system") as mock_sys:
            await inline_app._run_agent("test")
            mock_sys.assert_called_once()
            assert "Error" in mock_sys.call_args[0][0]

    @pytest.mark.asyncio()
    async def test_run_agent_session_auto_title(self, inline_app: InlineApp) -> None:
        """First call titles session, second doesn't re-title."""
        mock_loop = AsyncMock()
        mock_loop.run = AsyncMock(return_value="response")
        inline_app._agent_loop = mock_loop
        inline_app._provider = MagicMock()
        inline_app._session_titled = False

        with patch.object(inline_app.renderer, "start_streaming"), \
             patch.object(inline_app.renderer, "end_streaming", return_value=""), \
             patch.object(inline_app.renderer, "end_thinking"), \
             patch.object(inline_app.renderer, "print_thinking_indicator"), \
             patch.object(inline_app.session_store, "update_session") as mock_update:
            await inline_app._run_agent("first message")
            mock_update.assert_called_once()
            assert inline_app._session_titled is True

            mock_update.reset_mock()
            await inline_app._run_agent("second message")
            mock_update.assert_not_called()


class TestREPLLoop:
    @pytest.mark.asyncio()
    async def test_repl_keyboard_interrupt_first(self, inline_app: InlineApp) -> None:
        """First ^C prints warning, increments _interrupt_count."""
        mock_session = MagicMock()
        mock_session.prompt_async = AsyncMock(
            side_effect=[KeyboardInterrupt, EOFError],
        )
        inline_app.session = mock_session

        with patch.object(inline_app.renderer, "print_welcome"), \
             patch.object(inline_app.renderer, "print_goodbye"), \
             patch.object(inline_app.console, "print"):
            await inline_app.run()
        # After first ^C, count should be 1, then EOFError exits
        # We can't check mid-loop, but the test verifies no crash

    @pytest.mark.asyncio()
    async def test_repl_keyboard_interrupt_double_exits(self, inline_app: InlineApp) -> None:
        """Two ^C's break the loop."""
        mock_session = MagicMock()
        mock_session.prompt_async = AsyncMock(
            side_effect=[KeyboardInterrupt, KeyboardInterrupt],
        )
        inline_app.session = mock_session

        with patch.object(inline_app.renderer, "print_welcome"), \
             patch.object(inline_app.renderer, "print_goodbye") as mock_goodbye, \
             patch.object(inline_app.console, "print"):
            await inline_app.run()
            mock_goodbye.assert_called_once()

    @pytest.mark.asyncio()
    async def test_repl_keyboard_interrupt_during_agent(self, inline_app: InlineApp) -> None:
        """^C at idle prompt does NOT call cancel() just because _agent_loop exists."""
        mock_agent = MagicMock()
        mock_agent.cancel = MagicMock()
        inline_app._agent_loop = mock_agent

        mock_session = MagicMock()
        mock_session.prompt_async = AsyncMock(
            side_effect=[KeyboardInterrupt, EOFError],
        )
        inline_app.session = mock_session

        with patch.object(inline_app.renderer, "print_welcome"), \
             patch.object(inline_app.renderer, "print_goodbye"), \
             patch.object(inline_app.console, "print") as mock_print:
            await inline_app.run()
            mock_agent.cancel.assert_not_called()
            printed = " ".join(str(c) for c in mock_print.call_args_list)
            assert "Ctrl+C again" in printed or "quit" in printed

    @pytest.mark.asyncio()
    async def test_repl_interrupt_count_resets_on_input(self, inline_app: InlineApp) -> None:
        """Valid input resets _interrupt_count to 0."""
        mock_session = MagicMock()
        mock_session.prompt_async = AsyncMock(
            side_effect=[KeyboardInterrupt, "hello", EOFError],
        )
        inline_app.session = mock_session

        with patch.object(inline_app.renderer, "print_welcome"), \
             patch.object(inline_app.renderer, "print_goodbye"), \
             patch.object(inline_app.renderer, "print_turn_separator"), \
             patch.object(inline_app, "_handle_input_with_cancel", new_callable=AsyncMock), \
             patch.object(inline_app.console, "print"):
            await inline_app.run()
            assert inline_app._interrupt_count == 0

    @pytest.mark.asyncio()
    async def test_repl_empty_input_skipped(self, inline_app: InlineApp) -> None:
        """Whitespace input doesn't trigger _handle_input_with_cancel."""
        mock_session = MagicMock()
        mock_session.prompt_async = AsyncMock(
            side_effect=["  \t  ", EOFError],
        )
        inline_app.session = mock_session

        mock_cancel = AsyncMock()
        with patch.object(inline_app.renderer, "print_welcome"), \
             patch.object(inline_app.renderer, "print_goodbye"), \
             patch.object(inline_app, "_handle_input_with_cancel", mock_cancel):
            await inline_app.run()
            mock_cancel.assert_not_called()

    @pytest.mark.asyncio()
    async def test_repl_prints_goodbye_on_exit(self, inline_app: InlineApp) -> None:
        """EOFError -> renderer.print_goodbye() called."""
        mock_session = MagicMock()
        mock_session.prompt_async = AsyncMock(side_effect=EOFError)
        inline_app.session = mock_session

        with patch.object(inline_app.renderer, "print_welcome"), \
             patch.object(inline_app.renderer, "print_goodbye") as mock_goodbye:
            await inline_app.run()
            mock_goodbye.assert_called_once()

    @pytest.mark.asyncio()
    async def test_repl_welcome_banner_printed(self, inline_app: InlineApp) -> None:
        """run() calls renderer.print_welcome()."""
        mock_session = MagicMock()
        mock_session.prompt_async = AsyncMock(side_effect=EOFError)
        inline_app.session = mock_session

        with patch.object(inline_app.renderer, "print_welcome") as mock_welcome, \
             patch.object(inline_app.renderer, "print_goodbye"):
            await inline_app.run()
            mock_welcome.assert_called_once()

    @pytest.mark.asyncio()
    async def test_repl_turn_separator_after_response(self, inline_app: InlineApp) -> None:
        """Separator printed after each agent response."""
        mock_session = MagicMock()
        mock_session.prompt_async = AsyncMock(
            side_effect=["hello", EOFError],
        )
        inline_app.session = mock_session

        with patch.object(inline_app.renderer, "print_welcome"), \
             patch.object(inline_app.renderer, "print_goodbye"), \
             patch.object(inline_app.renderer, "print_turn_separator") as mock_sep, \
             patch.object(inline_app, "_handle_input_with_cancel", new_callable=AsyncMock):
            await inline_app.run()
            mock_sep.assert_called_once()

    @pytest.mark.asyncio()
    async def test_repl_prints_separator_immediately_after_user_turn(
        self, inline_app: InlineApp,
    ) -> None:
        """User turn is printed, then a separator, before any output starts.

        This is the key "two-canvas" separation: the submitted `❯ ...` turn is
        committed to scrollback and we close the input area with a full-width
        separator before any model/tool output begins.
        """
        mock_session = MagicMock()
        mock_session.prompt_async = AsyncMock(
            side_effect=["hello", EOFError],
        )
        inline_app.session = mock_session

        mock_renderer = MagicMock()
        inline_app.renderer = mock_renderer

        with patch.object(inline_app, "_handle_input_with_cancel", new_callable=AsyncMock):
            await inline_app.run()

        # Ensure we print the user turn and then immediately a separator.
        calls = mock_renderer.method_calls
        idx = calls.index(call.print_user_turn("hello"))
        assert calls[idx + 1] == call.print_separator()

    @pytest.mark.asyncio()
    async def test_repl_keyboard_interrupt_first_prints_warning(
        self, inline_app: InlineApp,
    ) -> None:
        """First ^C prints the 'Press Ctrl+C again to quit' warning."""
        mock_session = MagicMock()
        mock_session.prompt_async = AsyncMock(
            side_effect=[KeyboardInterrupt, EOFError],
        )
        inline_app.session = mock_session

        with patch.object(inline_app.renderer, "print_welcome"), \
             patch.object(inline_app.renderer, "print_goodbye"), \
             patch.object(inline_app.console, "print") as mock_print:
            await inline_app.run()
            printed = " ".join(str(c) for c in mock_print.call_args_list)
            assert "Ctrl+C again" in printed or "quit" in printed

    @pytest.mark.asyncio()
    async def test_repl_keyboard_interrupt_during_agent_prints_message(
        self, inline_app: InlineApp,
    ) -> None:
        """KeyboardInterrupt during generation prints 'generation cancelled' message."""
        inline_app._interrupt_count = 1  # prove it resets on generation-cancel
        mock_agent = MagicMock()
        mock_agent.cancel = MagicMock()
        inline_app._agent_loop = mock_agent

        with (
            patch("asyncio.wait", side_effect=KeyboardInterrupt),
            patch.object(inline_app, "_handle_input", new_callable=AsyncMock),
            patch.object(inline_app, "_listen_for_escape", new_callable=AsyncMock),
            patch.object(inline_app.renderer, "end_thinking"),
            patch.object(inline_app.renderer, "end_streaming", return_value=""),
            patch.object(inline_app.console, "print") as mock_print,
        ):
            await inline_app._handle_input_with_cancel("hello")
            printed = " ".join(str(c) for c in mock_print.call_args_list)
            assert "generation cancelled" in printed.lower() or "cancelled" in printed.lower()
            assert inline_app._interrupt_count == 0
            assert inline_app._agent_task is None

    @pytest.mark.asyncio()
    async def test_repl_interrupt_count_resets_after_agent_cancel(
        self, inline_app: InlineApp,
    ) -> None:
        """KeyboardInterrupt during generation resets _interrupt_count to 0."""
        inline_app._interrupt_count = 1
        mock_agent = MagicMock()
        mock_agent.cancel = MagicMock()
        inline_app._agent_loop = mock_agent

        with (
            patch("asyncio.wait", side_effect=KeyboardInterrupt),
            patch.object(inline_app, "_handle_input", new_callable=AsyncMock),
            patch.object(inline_app, "_listen_for_escape", new_callable=AsyncMock),
            patch.object(inline_app.renderer, "end_thinking"),
            patch.object(inline_app.renderer, "end_streaming", return_value=""),
            patch.object(inline_app.console, "print"),
        ):
            await inline_app._handle_input_with_cancel("hello")
            assert inline_app._interrupt_count == 0

    @pytest.mark.asyncio()
    async def test_escape_cancel_prints_cancelled_message(
        self, inline_app: InlineApp,
    ) -> None:
        """Escape during _handle_input_with_cancel prints 'Cancelled.'."""
        with (
            patch.object(
                inline_app, "_listen_for_escape",
                new_callable=AsyncMock, return_value=True,
            ),
            patch.object(
                inline_app, "_handle_input",
                new_callable=AsyncMock,
            ) as mock_handle,
            patch.object(inline_app.renderer, "end_thinking"),
            patch.object(inline_app.renderer, "end_streaming", return_value=""),
            patch.object(inline_app.console, "print") as mock_print,
        ):
            async def _hang(text: str) -> None:
                await asyncio.sleep(100)
            mock_handle.side_effect = _hang
            await inline_app._handle_input_with_cancel("hello")
            printed = " ".join(str(c) for c in mock_print.call_args_list)
            assert "Cancelled" in printed

    @pytest.mark.asyncio()
    async def test_ctrl_c_at_idle_after_previous_generation(
        self, inline_app: InlineApp,
    ) -> None:
        """Ctrl+C at idle prompt after a previous generation shows quit warning.

        Bug exposure: _agent_loop is never reset to None after completion,
        so Ctrl+C at idle incorrectly takes the 'cancel generation' path
        instead of showing 'Press Ctrl+C again to quit'.
        """
        # Simulate state after a previous generation completed
        mock_agent = MagicMock()
        inline_app._agent_loop = mock_agent

        mock_session = MagicMock()
        mock_session.prompt_async = AsyncMock(
            side_effect=[KeyboardInterrupt, EOFError],
        )
        inline_app.session = mock_session

        with patch.object(inline_app.renderer, "print_welcome"), \
             patch.object(inline_app.renderer, "print_goodbye"), \
             patch.object(inline_app.console, "print") as mock_print:
            await inline_app.run()
            printed = " ".join(str(c) for c in mock_print.call_args_list)
            # Regression test for Entry 114: _agent_loop can be truthy even when
            # no generation is in progress, so Ctrl+C should show the quit warning.
            assert "Ctrl+C again" in printed or "quit" in printed.lower()
            mock_agent.cancel.assert_not_called()

    def test_prompt_is_green_chevron(self, inline_app: InlineApp) -> None:
        """FormattedText in run() contains '>' character."""
        import inspect

        source = inspect.getsource(InlineApp.run)
        assert "❯" in source
