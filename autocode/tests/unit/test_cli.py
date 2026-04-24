"""Tests for AutoCode CLI commands."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from autocode.cli import app
from autocode.config import AutoCodeConfig

runner = CliRunner()


class TestCLIVersion:
    """Test version command."""

    def test_version_output(self) -> None:
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "autocode 0.1.0" in result.output


class TestCLIConfig:
    """Test config command."""

    def test_config_show(self) -> None:
        result = runner.invoke(app, ["config", "show"])
        assert result.exit_code == 0
        assert "ollama" in result.output or "openrouter" in result.output

    def test_config_check(self) -> None:
        result = runner.invoke(app, ["config", "check"])
        assert result.exit_code == 0

    def test_config_path(self) -> None:
        result = runner.invoke(app, ["config", "path"])
        assert result.exit_code == 0
        assert ".autocode" in result.output

    def test_config_invalid_action(self) -> None:
        result = runner.invoke(app, ["config", "invalid"])
        assert result.exit_code == 0
        assert "Unknown action" in result.output


class TestCLIConfigSet:
    """Test config set command."""

    def test_config_set_missing_value(self) -> None:
        result = runner.invoke(app, ["config", "set"])
        assert result.exit_code == 1

    def test_config_set_bad_format(self) -> None:
        result = runner.invoke(app, ["config", "set", "no-equals"])
        assert result.exit_code == 1

    def test_config_set_bad_section(self) -> None:
        result = runner.invoke(app, ["config", "set", "fake.key=value"])
        assert result.exit_code == 1
        assert "Unknown section" in result.output

    def test_config_set_bad_field(self) -> None:
        result = runner.invoke(app, ["config", "set", "llm.nonexistent=value"])
        assert result.exit_code == 1
        assert "Unknown field" in result.output


class TestCLIEdit:
    """Test edit command (stub)."""

    def test_edit_stub(self) -> None:
        result = runner.invoke(app, ["edit", "test.py", "add docstring"])
        assert result.exit_code == 0
        assert "not yet implemented" in result.output


class TestCLIHelp:
    """Test help output."""

    def test_no_args_starts_chat(self) -> None:
        # Bare `autocode` launches the chat command, not help text.
        mock_result = MagicMock(returncode=0)
        config = AutoCodeConfig()
        config.tui.alternate_screen = False

        with patch("autocode.cli.load_config", return_value=config):
            with patch("autocode.cli._find_tui_binary", return_value="/tmp/autocode-tui"):
                with patch("subprocess.run", return_value=mock_result) as mock_run:
                    result = runner.invoke(app, [])

        assert result.exit_code == 0
        mock_run.assert_called_once()
        args, _kwargs = mock_run.call_args
        assert args[0] == ["/tmp/autocode-tui"]

    def test_top_level_mode_launches_altscreen(self) -> None:
        mock_result = MagicMock(returncode=0)

        with patch("autocode.cli._find_tui_binary", return_value="/tmp/autocode-tui"):
            with patch("subprocess.run", return_value=mock_result) as mock_run:
                result = runner.invoke(app, ["--mode", "altscreen"])

        assert result.exit_code == 0
        mock_run.assert_called_once()
        args, _kwargs = mock_run.call_args
        assert args[0] == ["/tmp/autocode-tui", "--altscreen"]

    def test_top_level_attach_forwards_backend_address(self) -> None:
        mock_result = MagicMock(returncode=0)
        config = AutoCodeConfig()
        config.tui.alternate_screen = False

        with patch("autocode.cli.load_config", return_value=config):
            with patch("autocode.cli._find_tui_binary", return_value="/tmp/autocode-tui"):
                with patch("subprocess.run", return_value=mock_result) as mock_run:
                    result = runner.invoke(app, ["--attach", "127.0.0.1:8765"])

        assert result.exit_code == 0
        mock_run.assert_called_once()
        args, _kwargs = mock_run.call_args
        assert args[0] == ["/tmp/autocode-tui", "--attach", "127.0.0.1:8765"]


class TestCLIChat:
    def test_chat_launches_rust_tui_inline_by_default(self) -> None:
        mock_result = MagicMock(returncode=0)
        config = AutoCodeConfig()
        config.tui.alternate_screen = False

        with patch("autocode.cli.load_config", return_value=config):
            with patch("autocode.cli._find_tui_binary", return_value="/tmp/autocode-tui"):
                with patch("subprocess.run", return_value=mock_result) as mock_run:
                    result = runner.invoke(app, ["chat"])

        assert result.exit_code == 0
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert args[0] == ["/tmp/autocode-tui"]
        assert "env" in kwargs

    def test_chat_uses_saved_altscreen_default_when_configured(self) -> None:
        from autocode.config import AutoCodeConfig

        mock_result = MagicMock(returncode=0)
        config = AutoCodeConfig()
        config.tui.alternate_screen = True

        with patch("autocode.cli.load_config", return_value=config):
            with patch("autocode.cli._find_tui_binary", return_value="/tmp/autocode-tui"):
                with patch("subprocess.run", return_value=mock_result) as mock_run:
                    result = runner.invoke(app, ["chat"])

        assert result.exit_code == 0
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert args[0] == ["/tmp/autocode-tui", "--altscreen"]
        assert "env" in kwargs

    def test_chat_can_launch_rust_tui_in_alternate_screen_mode(self) -> None:
        mock_result = MagicMock(returncode=0)

        with patch("autocode.cli._find_tui_binary", return_value="/tmp/autocode-tui"):
            with patch("subprocess.run", return_value=mock_result) as mock_run:
                result = runner.invoke(app, ["chat", "--rust-altscreen"])

        assert result.exit_code == 0
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert args[0] == ["/tmp/autocode-tui", "--altscreen"]
        assert "env" in kwargs

    def test_chat_mode_flag_can_force_inline_over_saved_altscreen_default(self) -> None:
        from autocode.config import AutoCodeConfig

        mock_result = MagicMock(returncode=0)
        config = AutoCodeConfig()
        config.tui.alternate_screen = True

        with patch("autocode.cli.load_config", return_value=config):
            with patch("autocode.cli._find_tui_binary", return_value="/tmp/autocode-tui"):
                with patch("subprocess.run", return_value=mock_result) as mock_run:
                    result = runner.invoke(app, ["chat", "--mode", "inline"])

        assert result.exit_code == 0
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert args[0] == ["/tmp/autocode-tui"]
        assert "env" in kwargs

    def test_chat_mode_flag_can_request_altscreen(self) -> None:
        mock_result = MagicMock(returncode=0)

        with patch("autocode.cli._find_tui_binary", return_value="/tmp/autocode-tui"):
            with patch("subprocess.run", return_value=mock_result) as mock_run:
                result = runner.invoke(app, ["chat", "--mode", "altscreen"])

        assert result.exit_code == 0
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert args[0] == ["/tmp/autocode-tui", "--altscreen"]
        assert "env" in kwargs

    def test_chat_attach_forwards_backend_address(self) -> None:
        mock_result = MagicMock(returncode=0)
        config = AutoCodeConfig()
        config.tui.alternate_screen = False

        with patch("autocode.cli.load_config", return_value=config):
            with patch("autocode.cli._find_tui_binary", return_value="/tmp/autocode-tui"):
                with patch("subprocess.run", return_value=mock_result) as mock_run:
                    result = runner.invoke(app, ["chat", "--attach", "127.0.0.1:9000"])

        assert result.exit_code == 0
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert args[0] == ["/tmp/autocode-tui", "--attach", "127.0.0.1:9000"]
        assert "env" in kwargs


class TestCLIServe:
    def test_serve_accepts_tcp_transport_options(self) -> None:
        with patch("autocode.cli.load_config", return_value=AutoCodeConfig()):
            with patch("autocode.core.logging.setup_logging"):
                with patch("autocode.backend.server.main", new=AsyncMock()) as mock_main:
                    result = runner.invoke(
                        app,
                        ["serve", "--transport", "tcp", "--host", "0.0.0.0", "--port", "9900"],
                    )

        assert result.exit_code == 0
        mock_main.assert_awaited_once_with(
            transport="tcp",
            bind_host="0.0.0.0",
            port=9900,
        )

    def test_serve_rejects_invalid_transport(self) -> None:
        result = runner.invoke(app, ["serve", "--transport", "udp"])

        assert result.exit_code == 2
        assert "Invalid --transport" in result.output
