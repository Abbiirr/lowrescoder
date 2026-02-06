"""Tests for slash command router and commands."""

from __future__ import annotations

from hybridcoder.tui.commands import create_default_router


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
        """All 14 slash commands are registered."""
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
