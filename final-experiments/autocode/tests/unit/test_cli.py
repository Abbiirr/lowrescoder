"""Tests for AutoCode CLI commands."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from autocode.app.commands import create_default_router
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


class TestCLILegacyChat:
    @pytest.mark.asyncio()
    async def test_legacy_chat_dispatches_shared_slash_commands(self, monkeypatch) -> None:
        from autocode import cli

        config = AutoCodeConfig()
        prompts = iter(["/help", "exit"])
        printed: list[str] = []
        provider = MagicMock()

        monkeypatch.setattr(cli, "_get_provider", lambda _config: provider)
        monkeypatch.setattr(cli.console, "input", lambda _prompt: next(prompts))
        monkeypatch.setattr(
            cli.console,
            "print",
            lambda *args, **_kwargs: printed.append(" ".join(str(arg) for arg in args)),
        )
        with patch("autocode.cli._stream_response", new=AsyncMock()) as stream:
            await cli._chat_loop(config)

        stream.assert_not_awaited()
        assert any("/help" in line for line in printed)
        assert any("/model" in line for line in printed)

    def test_textual_and_compat_imports_use_shared_command_catalog(self) -> None:
        import autocode.app.commands as app_commands
        import autocode.tui.commands as tui_commands
        from autocode.tui.app import AutoCodeApp

        app = AutoCodeApp(config=AutoCodeConfig())
        shared_names = {cmd.name for cmd in create_default_router().get_all()}
        textual_names = {cmd.name for cmd in app.command_router.get_all()}

        assert tui_commands is app_commands
        assert {"help", "kairos", "recipe", "marketplace"} <= textual_names
        assert textual_names == shared_names


class TestCLIKairos:
    def test_daemon_watch_is_default_off(self, tmp_path) -> None:
        result = runner.invoke(app, ["daemon", "--watch", str(tmp_path)])

        assert result.exit_code == 0
        assert "KAIROS is disabled" in result.output

    def test_daemon_read_only_help_describes_backend_guard(self) -> None:
        result = runner.invoke(app, ["daemon", "--help"])

        assert result.exit_code == 0
        assert "backend read-only guard" in result.output
        assert "Block proactive mutation intent" not in result.output

    def test_kairos_audit_reads_jsonl(self, tmp_path) -> None:
        log_path = tmp_path / "kairos.jsonl"
        log_path.write_text(
            '{"session_id":"s1","action":"tool_call_completed",'
            '"files_changed":["src/app.py"],"metadata":{"tool_name":"edit_file"}}\n',
            encoding="utf-8",
        )

        result = runner.invoke(app, ["kairos", "audit", "--log-path", str(log_path)])

        assert result.exit_code == 0
        assert "tool_call_completed" in result.output
        assert "src/app.py" in result.output

    def test_daemon_once_sends_tick_when_enabled(self, tmp_path, monkeypatch) -> None:
        config = AutoCodeConfig()
        sent: list[dict] = []

        async def fake_send_tick(**kwargs):
            sent.append(kwargs)
            return {"ok": True, "tick_id": kwargs["tick_id"]}

        monkeypatch.setenv("AUTOCODE_FEATURE_KAIROS", "true")
        with patch("autocode.cli.load_config", return_value=config):
            with patch("autocode.agent.proactive.send_tick_rpc", new=fake_send_tick):
                result = runner.invoke(
                    app,
                    [
                        "daemon",
                        "--watch",
                        str(tmp_path),
                        "--once",
                        "--no-dry-run",
                        "--attach",
                        "127.0.0.1:9999",
                    ],
                )

        assert result.exit_code == 0
        assert len(sent) == 1
        assert sent[0]["host"] == "127.0.0.1"
        assert sent[0]["port"] == 9999
        assert sent[0]["tick_id"]
        assert sent[0]["read_only"] is True

    def test_daemon_cost_cap_zero_skips_tick(self, tmp_path, monkeypatch) -> None:
        config = AutoCodeConfig()
        config.agent.cost_limit_usd = 0.0
        monkeypatch.setenv("AUTOCODE_FEATURE_KAIROS", "true")

        with patch("autocode.cli.load_config", return_value=config):
            with patch("autocode.agent.proactive.send_tick_rpc", new=AsyncMock()) as send:
                result = runner.invoke(
                    app,
                    ["daemon", "--watch", str(tmp_path), "--once"],
                )

        assert result.exit_code == 0
        assert "cost cap" in result.output.lower()
        send.assert_not_called()

    def test_daemon_max_ticks_sends_repeated_ticks(self, tmp_path, monkeypatch) -> None:
        config = AutoCodeConfig()
        sent: list[dict] = []

        async def fake_send_tick(**kwargs):
            sent.append(kwargs)
            return {"ok": True, "tick_id": kwargs["tick_id"]}

        monkeypatch.setenv("AUTOCODE_FEATURE_KAIROS", "true")
        with patch("autocode.cli.load_config", return_value=config):
            with patch("autocode.agent.proactive.send_tick_rpc", new=fake_send_tick):
                with patch("time.sleep") as sleep:
                    result = runner.invoke(
                        app,
                        [
                            "daemon",
                            "--watch",
                            str(tmp_path),
                            "--no-dry-run",
                            "--interval",
                            "0.01",
                            "--max-ticks",
                            "3",
                        ],
                    )

        assert result.exit_code == 0
        assert len(sent) == 3
        assert len({call["tick_id"] for call in sent}) == 3
        assert sleep.call_count == 2


class TestCLIExec:
    """Test headless exec command behavior."""

    def test_json_mode_runner_construction_failure_emits_error_event(self) -> None:
        with patch("autocode.cli.load_config", return_value=AutoCodeConfig()):
            with patch(
                "autocode.backend.headless_runner.HeadlessRunner",
                side_effect=RuntimeError("cannot create session"),
            ):
                result = runner.invoke(app, ["exec", "hello", "--json"])

        assert result.exit_code == 1
        event = json.loads(result.stdout.strip())
        assert event["type"] == "error"
        assert event["protocol_version"] == "0.2.0-harness"
        assert event["message"] == "cannot create session"

    def test_json_mode_auto_approve_flag_is_explicit(self) -> None:
        mock_runner = MagicMock()
        mock_runner.run = AsyncMock(return_value=None)

        with patch("autocode.cli.load_config", return_value=AutoCodeConfig()):
            with patch(
                "autocode.backend.headless_runner.HeadlessRunner",
                return_value=mock_runner,
            ) as runner_cls:
                result = runner.invoke(app, ["exec", "hello", "--json", "--auto-approve"])

        assert result.exit_code == 0
        assert runner_cls.call_args.kwargs["auto_approve"] is True

    def test_json_mode_denies_approvals_by_default(self) -> None:
        mock_runner = MagicMock()
        mock_runner.run = AsyncMock(return_value=None)

        with patch("autocode.cli.load_config", return_value=AutoCodeConfig()):
            with patch(
                "autocode.backend.headless_runner.HeadlessRunner",
                return_value=mock_runner,
            ) as runner_cls:
                result = runner.invoke(app, ["exec", "hello", "--json"])

        assert result.exit_code == 0
        assert runner_cls.call_args.kwargs["auto_approve"] is False


class TestCLITelemetry:
    def test_telemetry_summary_uses_aggregator(self) -> None:
        with patch("autocode.telemetry.aggregator.TelemetryAggregator") as agg_cls:
            agg = agg_cls.return_value
            agg.summary.return_value.total_events = 2
            agg.summary.return_value.by_kind = {"turn_start": 1, "turn_completed": 1}
            agg.summary.return_value.by_session = {"s1": 2}
            agg.summary.return_value.alerts = []

            result = runner.invoke(app, ["telemetry", "summary"])

        assert result.exit_code == 0
        assert "turn_start" in result.output
        assert "turn_completed" in result.output

    def test_telemetry_summary_prints_alerts(self) -> None:
        with patch("autocode.telemetry.aggregator.TelemetryAggregator") as agg_cls:
            agg = agg_cls.return_value
            agg.summary.return_value.total_events = 22
            agg.summary.return_value.by_kind = {
                "kairos_tick": 20,
                "kairos_anti_narration": 2,
            }
            agg.summary.return_value.by_session = {}
            agg.summary.return_value.alerts = [
                "KAIROS anti-narration violations are 10.0% of ticks (2/20), above 5.0%"
            ]

            result = runner.invoke(app, ["telemetry", "summary"])

        assert result.exit_code == 0
        assert "Alerts:" in result.output
        assert "anti-narration violations are 10.0%" in result.output

    def test_telemetry_purge_deletes_store(self, tmp_path, monkeypatch) -> None:
        from autocode.telemetry.store import telemetry_root

        monkeypatch.setenv("HOME", str(tmp_path))
        root = telemetry_root()
        root.mkdir(parents=True)
        (root / "events-2026-04-30.jsonl").write_text("{}\n")

        result = runner.invoke(app, ["telemetry", "purge"])

        assert result.exit_code == 0
        assert not root.exists()

    def test_telemetry_public_report_writes_output(self, tmp_path) -> None:
        with patch("autocode.telemetry.aggregator.TelemetryAggregator") as agg_cls:
            agg = agg_cls.return_value
            agg.public_report.return_value = {
                "total_events": 1,
                "by_kind": {"turn_completed": 1},
                "drift_events": 0,
                "eval_events": 0,
            }
            output = tmp_path / "public-stats.json"

            result = runner.invoke(
                app,
                ["telemetry", "public-report", "--output", str(output)],
            )

        assert result.exit_code == 0
        assert json.loads(output.read_text(encoding="utf-8"))["total_events"] == 1
        assert str(output) in result.output


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
                        ["serve", "--transport", "tcp", "--host", "127.0.0.1", "--port", "9900"],
                    )

        assert result.exit_code == 0
        mock_main.assert_awaited_once_with(
            transport="tcp",
            bind_host="127.0.0.1",
            port=9900,
        )

    def test_serve_rejects_non_loopback_tcp_host_by_default(self) -> None:
        with patch("autocode.cli.load_config", return_value=AutoCodeConfig()):
            with patch("autocode.core.logging.setup_logging"):
                with patch("autocode.backend.server.main", new=AsyncMock()) as mock_main:
                    result = runner.invoke(
                        app,
                        ["serve", "--transport", "tcp", "--host", "0.0.0.0", "--port", "9900"],
                    )

        assert result.exit_code == 2
        assert "Refusing non-loopback TCP bind host" in result.output
        mock_main.assert_not_awaited()

    def test_serve_rejects_invalid_transport(self) -> None:
        result = runner.invoke(app, ["serve", "--transport", "udp"])

        assert result.exit_code == 2
        assert "Invalid --transport" in result.output


class TestCLIMCPServe:
    def test_mcp_serve_help_exposes_stdio_options(self) -> None:
        result = runner.invoke(app, ["mcp-serve", "--help"])

        assert result.exit_code == 0
        assert "--transport" in result.output
        assert "stdio" in result.output
        assert "--project-root" in result.output
        assert "--audit-log-path" in result.output

    def test_mcp_serve_stdio_runs_mcp_server(self, tmp_path: Path) -> None:
        mock_server = MagicMock()
        audit_path = tmp_path / "mcp_audit.jsonl"

        with patch(
            "autocode.external.mcp_server.MCPServer",
            return_value=mock_server,
        ) as server_cls:
            result = runner.invoke(
                app,
                [
                    "mcp-serve",
                    "--transport",
                    "stdio",
                    "--project-root",
                    str(tmp_path),
                    "--audit-log-path",
                    str(audit_path),
                ],
            )

        assert result.exit_code == 0
        server_cls.assert_called_once()
        config = server_cls.call_args.args[0]
        assert config.enabled is True
        assert config.transport == "stdio"
        assert config.project_root == tmp_path
        assert config.audit_log_path == audit_path
        mock_server.run.assert_called_once()
