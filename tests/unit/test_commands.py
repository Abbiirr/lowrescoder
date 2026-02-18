"""Tests for slash command router and commands."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from autocode.tui.commands import create_default_router


async def _noop_handler(app: object, args: str) -> None:
    pass


class TestCommandRouter:
    def test_dispatch_help(self) -> None:
        """The /help command is dispatched correctly."""
        router = create_default_router()
        result = router.dispatch("/help")
        assert result is not None
        cmd, args = result
        assert cmd.name == "help"

    def test_dispatch_mode(self) -> None:
        """The /mode command parses arguments."""
        router = create_default_router()
        result = router.dispatch("/mode auto")
        assert result is not None
        cmd, args = result
        assert cmd.name == "mode"
        assert args == "auto"

    def test_dispatch_with_alias(self) -> None:
        """Aliases resolve to the correct command."""
        router = create_default_router()

        result = router.dispatch("/q")
        assert result is not None
        cmd, args = result
        assert cmd.name == "exit"

        result2 = router.dispatch("/h")
        assert result2 is not None
        assert result2[0].name == "help"

        result3 = router.dispatch("/m gpt-4")
        assert result3 is not None
        assert result3[0].name == "model"
        assert result3[1] == "gpt-4"

    def test_unknown_command(self) -> None:
        """Unknown commands return None."""
        router = create_default_router()
        assert router.dispatch("/nonexistent") is None
        assert router.dispatch("hello") is None  # not a command at all

    def test_compact_command(self) -> None:
        """The /compact command is registered."""
        router = create_default_router()
        result = router.dispatch("/compact")
        assert result is not None
        cmd, args = result
        assert cmd.name == "compact"

    def test_all_commands_registered(self) -> None:
        """All 17 slash commands are registered."""
        router = create_default_router()
        commands = router.get_all()
        names = {c.name for c in commands}
        expected = {
            "exit",
            "new",
            "sessions",
            "resume",
            "help",
            "model",
            "mode",
            "compact",
            "init",
            "shell",
            "copy",
            "freeze",
            "thinking",
            "clear",
            "index",
            "tasks",
            "plan",
            "memory",
            "checkpoint",
        }
        assert names == expected

    def test_shell_command_dispatches(self) -> None:
        """The /shell command is dispatched correctly."""
        router = create_default_router()
        result = router.dispatch("/shell on")
        assert result is not None
        cmd, args = result
        assert cmd.name == "shell"
        assert args == "on"

    def test_shell_command_no_args(self) -> None:
        """The /shell command with no args dispatches correctly."""
        router = create_default_router()
        result = router.dispatch("/shell")
        assert result is not None
        cmd, args = result
        assert cmd.name == "shell"
        assert args == ""

    def test_copy_command_dispatches(self) -> None:
        """The /copy command is dispatched correctly."""
        router = create_default_router()
        result = router.dispatch("/copy")
        assert result is not None
        cmd, args = result
        assert cmd.name == "copy"

    def test_copy_all_dispatches(self) -> None:
        """The /copy all command passes 'all' as args."""
        router = create_default_router()
        result = router.dispatch("/copy all")
        assert result is not None
        cmd, args = result
        assert cmd.name == "copy"
        assert args == "all"

    def test_copy_alias_cp(self) -> None:
        """The /cp alias resolves to /copy."""
        router = create_default_router()
        result = router.dispatch("/cp")
        assert result is not None
        assert result[0].name == "copy"

    def test_copy_n_dispatches(self) -> None:
        """The /copy 2 command passes '2' as args."""
        router = create_default_router()
        result = router.dispatch("/copy 2")
        assert result is not None
        cmd, args = result
        assert cmd.name == "copy"
        assert args == "2"

    def test_copy_last_n_dispatches(self) -> None:
        """The /copy last 5 command passes 'last 5' as args."""
        router = create_default_router()
        result = router.dispatch("/copy last 5")
        assert result is not None
        cmd, args = result
        assert cmd.name == "copy"
        assert args == "last 5"

    def test_freeze_command_dispatches(self) -> None:
        """The /freeze command is dispatched correctly."""
        router = create_default_router()
        result = router.dispatch("/freeze")
        assert result is not None
        cmd, args = result
        assert cmd.name == "freeze"

    def test_freeze_alias_scroll_lock(self) -> None:
        """The /scroll-lock alias resolves to /freeze."""
        router = create_default_router()
        result = router.dispatch("/scroll-lock")
        assert result is not None
        assert result[0].name == "freeze"


def _make_mock_app(tmp_path: Path) -> MagicMock:
    """Create a mock app with real SessionStore and config for handler tests."""
    from autocode.config import AutoCodeConfig
    from autocode.session.store import SessionStore

    config = AutoCodeConfig()
    config.tui.session_db_path = str(tmp_path / "test.db")
    store = SessionStore(str(tmp_path / "test.db"))
    sid = store.create_session(
        title="Test session",
        model="test-model",
        provider="ollama",
        project_dir=str(tmp_path),
    )

    app = MagicMock()
    app.session_store = store
    app.session_id = sid
    app.config = config
    app.project_root = tmp_path
    app.command_router = create_default_router()

    messages: list[str] = []
    app.add_system_message = lambda msg: messages.append(msg)
    app._messages = messages  # expose for assertions

    app.approval_mode = config.tui.approval_mode
    app.shell_enabled = config.shell.enabled
    app.show_thinking = False

    return app


class TestHandleExit:
    @pytest.mark.asyncio()
    async def test_exit_raises_eof(self, tmp_path: Path) -> None:
        """_handle_exit raises EOFError."""
        from autocode.tui.commands import _handle_exit

        app = _make_mock_app(tmp_path)
        app.exit_app.side_effect = EOFError
        with pytest.raises(EOFError):
            await _handle_exit(app, "")


class TestHandleNew:
    @pytest.mark.asyncio()
    async def test_new_creates_session(self, tmp_path: Path) -> None:
        """_handle_new creates a new session with default title."""
        from autocode.tui.commands import _handle_new

        app = _make_mock_app(tmp_path)
        old_id = app.session_id
        await _handle_new(app, "")
        # session_id should be updated
        assert app.session_id != old_id
        assert "New session" in app._messages[-1]

    @pytest.mark.asyncio()
    async def test_new_with_custom_title(self, tmp_path: Path) -> None:
        """_handle_new uses custom title when provided."""
        from autocode.tui.commands import _handle_new

        app = _make_mock_app(tmp_path)
        await _handle_new(app, "My Custom Title")
        assert "My Custom Title" in app._messages[-1]


class TestHandleHelp:
    @pytest.mark.asyncio()
    async def test_help_lists_all_commands(self, tmp_path: Path) -> None:
        """_handle_help lists all 14 commands."""
        from autocode.tui.commands import _handle_help

        app = _make_mock_app(tmp_path)
        await _handle_help(app, "")
        output = app._messages[-1]
        assert "Available commands" in output
        # Check all 14 commands are mentioned
        for name in ["exit", "new", "sessions", "resume", "help", "model",
                      "mode", "compact", "init", "shell", "copy", "freeze",
                      "thinking", "clear"]:
            assert f"/{name}" in output


class TestHandleModel:
    @pytest.mark.asyncio()
    async def test_model_no_args_shows_current(self, tmp_path: Path) -> None:
        """_handle_model with no args shows current model."""
        from autocode.tui.commands import _handle_model

        app = _make_mock_app(tmp_path)
        with patch("autocode.tui.commands._list_ollama_models", return_value=[]):
            await _handle_model(app, "")
        assert "Current model" in app._messages[-1]

    @pytest.mark.asyncio()
    async def test_model_set_changes_config(self, tmp_path: Path) -> None:
        """_handle_model with arg changes model."""
        from autocode.tui.commands import _handle_model

        app = _make_mock_app(tmp_path)
        await _handle_model(app, "llama3")
        assert app.config.llm.model == "llama3"
        assert "llama3" in app._messages[-1]


class TestHandleMode:
    @pytest.mark.asyncio()
    async def test_mode_no_args_shows_current(self, tmp_path: Path) -> None:
        """_handle_mode with no args shows current mode."""
        from autocode.tui.commands import _handle_mode

        app = _make_mock_app(tmp_path)
        await _handle_mode(app, "")
        assert "Current mode" in app._messages[-1]

    @pytest.mark.asyncio()
    async def test_mode_set_valid(self, tmp_path: Path) -> None:
        """_handle_mode sets valid mode."""
        from autocode.tui.commands import _handle_mode

        app = _make_mock_app(tmp_path)
        await _handle_mode(app, "auto")
        assert app.approval_mode == "auto"
        assert "auto" in app._messages[-1]

    @pytest.mark.asyncio()
    async def test_mode_set_invalid_rejected(self, tmp_path: Path) -> None:
        """_handle_mode rejects invalid mode."""
        from autocode.tui.commands import _handle_mode

        app = _make_mock_app(tmp_path)
        await _handle_mode(app, "invalid-mode")
        assert "Invalid mode" in app._messages[-1]


class TestHandleCompact:
    @pytest.mark.asyncio()
    async def test_compact_few_messages_early_return(self, tmp_path: Path) -> None:
        """_handle_compact returns early with <4 messages."""
        from autocode.tui.commands import _handle_compact

        app = _make_mock_app(tmp_path)
        # Add only 2 messages
        app.session_store.add_message(app.session_id, "user", "hello")
        app.session_store.add_message(app.session_id, "assistant", "hi")
        await _handle_compact(app, "")
        assert "Not enough" in app._messages[-1]

    @pytest.mark.asyncio()
    async def test_compact_enough_messages(self, tmp_path: Path) -> None:
        """_handle_compact compacts when enough messages exist."""
        from autocode.tui.commands import _handle_compact

        app = _make_mock_app(tmp_path)
        for i in range(6):
            role = "user" if i % 2 == 0 else "assistant"
            app.session_store.add_message(app.session_id, role, f"msg {i}")
        await _handle_compact(app, "")
        assert "Compacted" in app._messages[-1]


class TestHandleShell:
    @pytest.mark.asyncio()
    async def test_shell_on(self, tmp_path: Path) -> None:
        """_handle_shell enables shell."""
        from autocode.tui.commands import _handle_shell

        app = _make_mock_app(tmp_path)
        await _handle_shell(app, "on")
        assert app.shell_enabled is True
        assert "enabled" in app._messages[-1]

    @pytest.mark.asyncio()
    async def test_shell_off(self, tmp_path: Path) -> None:
        """_handle_shell disables shell."""
        from autocode.tui.commands import _handle_shell

        app = _make_mock_app(tmp_path)
        await _handle_shell(app, "off")
        assert app.shell_enabled is False
        assert "disabled" in app._messages[-1]

    @pytest.mark.asyncio()
    async def test_shell_no_args_shows_status(self, tmp_path: Path) -> None:
        """_handle_shell with no args shows status."""
        from autocode.tui.commands import _handle_shell

        app = _make_mock_app(tmp_path)
        await _handle_shell(app, "")
        output = app._messages[-1]
        assert "enabled" in output or "disabled" in output


class TestHandleCopy:
    @pytest.mark.asyncio()
    async def test_copy_no_args_copies_last(self, tmp_path: Path) -> None:
        """_handle_copy with no args copies last assistant message."""
        from autocode.tui.commands import _handle_copy

        app = _make_mock_app(tmp_path)
        app.session_store.add_message(app.session_id, "assistant", "response text")
        app.copy_to_clipboard = MagicMock(return_value=True)
        await _handle_copy(app, "")
        app.copy_to_clipboard.assert_called_once_with("response text")
        assert "Copied" in app._messages[-1]

    @pytest.mark.asyncio()
    async def test_copy_n(self, tmp_path: Path) -> None:
        """_handle_copy N copies Nth-last assistant message."""
        from autocode.tui.commands import _handle_copy

        app = _make_mock_app(tmp_path)
        app.session_store.add_message(app.session_id, "assistant", "first")
        app.session_store.add_message(app.session_id, "assistant", "second")
        app.copy_to_clipboard = MagicMock(return_value=True)
        await _handle_copy(app, "2")
        app.copy_to_clipboard.assert_called_once_with("first")

    @pytest.mark.asyncio()
    async def test_copy_all(self, tmp_path: Path) -> None:
        """_handle_copy all copies all messages."""
        from autocode.tui.commands import _handle_copy

        app = _make_mock_app(tmp_path)
        app.session_store.add_message(app.session_id, "user", "hello")
        app.session_store.add_message(app.session_id, "assistant", "hi")
        app.copy_to_clipboard = MagicMock(return_value=True)
        await _handle_copy(app, "all")
        call_text = app.copy_to_clipboard.call_args[0][0]
        assert "hello" in call_text
        assert "hi" in call_text

    @pytest.mark.asyncio()
    async def test_copy_last_n(self, tmp_path: Path) -> None:
        """_handle_copy last N copies last N messages."""
        from autocode.tui.commands import _handle_copy

        app = _make_mock_app(tmp_path)
        app.session_store.add_message(app.session_id, "user", "u1")
        app.session_store.add_message(app.session_id, "assistant", "a1")
        app.session_store.add_message(app.session_id, "user", "u2")
        app.copy_to_clipboard = MagicMock(return_value=True)
        await _handle_copy(app, "last 2")
        call_text = app.copy_to_clipboard.call_args[0][0]
        assert "a1" in call_text
        assert "u2" in call_text

    @pytest.mark.asyncio()
    async def test_copy_no_messages(self, tmp_path: Path) -> None:
        """_handle_copy with no assistant messages shows error."""
        from autocode.tui.commands import _handle_copy

        app = _make_mock_app(tmp_path)
        await _handle_copy(app, "")
        assert "No assistant messages" in app._messages[-1]

    @pytest.mark.asyncio()
    async def test_copy_clipboard_fail(self, tmp_path: Path) -> None:
        """_handle_copy shows fallback when clipboard fails."""
        from autocode.tui.commands import _handle_copy

        app = _make_mock_app(tmp_path)
        app.session_store.add_message(app.session_id, "assistant", "response")
        app.copy_to_clipboard = MagicMock(return_value=False)
        await _handle_copy(app, "")
        assert "Clipboard unavailable" in app._messages[-1]


class TestHandleThinking:
    @pytest.mark.asyncio()
    async def test_thinking_toggles(self, tmp_path: Path) -> None:
        """_handle_thinking toggles show_thinking on/off."""
        from autocode.tui.commands import _handle_thinking

        app = _make_mock_app(tmp_path)
        assert app.show_thinking is False
        await _handle_thinking(app, "")
        assert app.show_thinking is True
        assert "on" in app._messages[-1]


class TestHandleClear:
    @pytest.mark.asyncio()
    async def test_clear_writes_ansi_and_message(self, tmp_path: Path) -> None:
        """_handle_clear writes ANSI clear + confirmation."""
        from autocode.tui.commands import _handle_clear

        app = _make_mock_app(tmp_path)
        with patch("sys.stdout"):
            await _handle_clear(app, "")
        assert "cleared" in app._messages[-1].lower()


class TestHandleFreeze:
    @pytest.mark.asyncio()
    async def test_freeze_inline_mode(self, tmp_path: Path) -> None:
        """_handle_freeze in inline mode shows 'not needed' message."""
        from autocode.tui.commands import _handle_freeze

        app = _make_mock_app(tmp_path)
        # MagicMock doesn't have query_one by default (no hasattr match)
        del app.query_one
        await _handle_freeze(app, "")
        assert "not needed" in app._messages[-1].lower()


class TestHandleInit:
    @pytest.mark.asyncio()
    async def test_init_creates_memory(self, tmp_path: Path) -> None:
        """_handle_init creates memory.md."""
        from autocode.tui.commands import _handle_init

        app = _make_mock_app(tmp_path)
        await _handle_init(app, "")
        memory_file = tmp_path / ".autocode" / "memory.md"
        assert memory_file.exists()
        assert "Created" in app._messages[-1]

    @pytest.mark.asyncio()
    async def test_init_already_exists(self, tmp_path: Path) -> None:
        """_handle_init reports if memory.md already exists."""
        from autocode.tui.commands import _handle_init

        app = _make_mock_app(tmp_path)
        memory_dir = tmp_path / ".autocode"
        memory_dir.mkdir(parents=True)
        (memory_dir / "memory.md").write_text("existing")
        await _handle_init(app, "")
        assert "already exists" in app._messages[-1]

    @pytest.mark.asyncio()
    async def test_init_reads_key_files(self, tmp_path: Path) -> None:
        """_handle_init includes key files in memory."""
        from autocode.tui.commands import _handle_init

        app = _make_mock_app(tmp_path)
        (tmp_path / "README.md").write_text("# Test Project")
        (tmp_path / "pyproject.toml").write_text("[tool.poetry]\nname = 'test'")
        await _handle_init(app, "")
        memory_file = tmp_path / ".autocode" / "memory.md"
        content = memory_file.read_text()
        assert "README.md" in content
        assert "pyproject.toml" in content


class TestTitleTruncation:
    @pytest.mark.asyncio()
    async def test_resume_truncates_long_title(self, tmp_path: Path) -> None:
        """/resume truncates session titles longer than 40 chars."""
        from autocode.config import AutoCodeConfig
        from autocode.session.store import SessionStore
        from autocode.tui.commands import _handle_resume

        config = AutoCodeConfig()
        config.tui.session_db_path = str(tmp_path / "test.db")
        store = SessionStore(str(tmp_path / "test.db"))

        # Create a session with a very long title
        long_title = "A" * 100
        store.create_session(
            title=long_title,
            model="test-model",
            provider="ollama",
            project_dir=str(tmp_path),
        )

        app = MagicMock()
        app.session_store = store
        app.config = config
        app.project_root = tmp_path

        messages: list[str] = []
        app.add_system_message = lambda msg: messages.append(msg)

        await _handle_resume(app, "")

        output = "\n".join(messages)
        # Full 100-char title should NOT appear
        assert long_title not in output
        # Truncated version should appear
        assert "..." in output

    @pytest.mark.asyncio()
    async def test_sessions_truncates_long_title(self, tmp_path: Path) -> None:
        """/sessions truncates session titles longer than 40 chars."""
        from autocode.config import AutoCodeConfig
        from autocode.session.store import SessionStore
        from autocode.tui.commands import _handle_sessions

        config = AutoCodeConfig()
        config.tui.session_db_path = str(tmp_path / "test.db")
        store = SessionStore(str(tmp_path / "test.db"))

        long_title = "B" * 100
        store.create_session(
            title=long_title,
            model="test-model",
            provider="ollama",
            project_dir=str(tmp_path),
        )

        app = MagicMock()
        app.session_store = store
        app.config = config
        app.project_root = tmp_path

        messages: list[str] = []
        app.add_system_message = lambda msg: messages.append(msg)

        await _handle_sessions(app, "")

        output = "\n".join(messages)
        assert long_title not in output
        assert "..." in output


class TestSystemPromptContent:
    """Test system prompt includes required policy rules (BUG-24)."""

    def test_write_file_directory_rule_in_prompt(self) -> None:
        """SYSTEM_PROMPT includes the path-scoped write intent rule."""
        from autocode.agent.prompts import SYSTEM_PROMPT

        assert "write files directly inside that directory" in SYSTEM_PROMPT
        assert "write_file tool automatically creates parent directories" in SYSTEM_PROMPT

    def test_build_system_prompt_includes_rule(self) -> None:
        """build_system_prompt() output includes the directory write rule."""
        from autocode.agent.prompts import build_system_prompt

        prompt = build_system_prompt()
        assert "write files directly inside that directory" in prompt
