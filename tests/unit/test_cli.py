"""Tests for AutoCode CLI commands."""

from __future__ import annotations

from typer.testing import CliRunner

from autocode.cli import app

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

    def test_no_args_shows_help(self) -> None:
        result = runner.invoke(app, [])
        # Typer returns exit code 0 for --help, but 2 for no_args_is_help
        assert result.exit_code in (0, 2)
        assert "Edge-native" in result.output or "Usage" in result.output
