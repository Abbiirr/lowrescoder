"""Tests for InlineApp."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

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
    async def test_approval_prompt_always(self, inline_app: InlineApp) -> None:
        """Approval prompt returns True and enables shell on 'Always'."""
        with patch.object(inline_app, "_arrow_select", new_callable=AsyncMock, return_value="Always"):
            result = await inline_app._approval_prompt("run_command", {"command": "ls"})
            assert result is True

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
