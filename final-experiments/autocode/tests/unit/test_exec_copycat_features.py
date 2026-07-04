"""Tests for the two clean-room puku-cli features landed on ``autocode exec``:

  * ``--permission-mode`` (puku's session permission enum), and
  * ``--max-budget-usd`` (puku's per-run USD spend cap).

Both are additive: omitting them preserves AutoCode's existing exec behavior. The
CLI tests assert the flags thread through to the headless runner; the runner test
asserts the mode actually changes approval behavior.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from autocode.cli import app
from autocode.config import AutoCodeConfig

runner = CliRunner()


def test_permission_mode_threads_to_runner() -> None:
    mock_runner = MagicMock()
    mock_runner.run = AsyncMock(return_value=None)
    with patch("autocode.cli.load_config", return_value=AutoCodeConfig()):
        with patch(
            "autocode.backend.headless_runner.HeadlessRunner",
            return_value=mock_runner,
        ) as runner_cls:
            result = runner.invoke(
                app, ["exec", "hi", "--json", "--permission-mode", "bypassPermissions"]
            )
    assert result.exit_code == 0
    assert runner_cls.call_args.kwargs["permission_mode"] == "bypassPermissions"


def test_max_budget_usd_threads_to_runner() -> None:
    mock_runner = MagicMock()
    mock_runner.run = AsyncMock(return_value=None)
    with patch("autocode.cli.load_config", return_value=AutoCodeConfig()):
        with patch(
            "autocode.backend.headless_runner.HeadlessRunner",
            return_value=mock_runner,
        ) as runner_cls:
            result = runner.invoke(
                app, ["exec", "hi", "--json", "--max-budget-usd", "1.5"]
            )
    assert result.exit_code == 0
    assert runner_cls.call_args.kwargs["max_budget_usd"] == 1.5


def test_system_prompt_flags_thread_to_runner() -> None:
    mock_runner = MagicMock()
    mock_runner.run = AsyncMock(return_value=None)
    with patch("autocode.cli.load_config", return_value=AutoCodeConfig()):
        with patch(
            "autocode.backend.headless_runner.HeadlessRunner",
            return_value=mock_runner,
        ) as runner_cls:
            result = runner.invoke(
                app,
                ["exec", "hi", "--json",
                 "--system-prompt", "Be terse.",
                 "--append-system-prompt", "Cite sources."],
            )
    assert result.exit_code == 0
    assert runner_cls.call_args.kwargs["system_prompt"] == "Be terse."
    assert runner_cls.call_args.kwargs["append_system_prompt"] == "Cite sources."


def test_add_dir_flags_thread_to_runner() -> None:
    mock_runner = MagicMock()
    mock_runner.run = AsyncMock(return_value=None)
    with patch("autocode.cli.load_config", return_value=AutoCodeConfig()):
        with patch(
            "autocode.backend.headless_runner.HeadlessRunner",
            return_value=mock_runner,
        ) as runner_cls:
            result = runner.invoke(
                app,
                ["exec", "hi", "--json", "--add-dir", "/tmp/a", "--add-dir", "/tmp/b"],
            )
    assert result.exit_code == 0
    assert runner_cls.call_args.kwargs["add_dirs"] == ("/tmp/a", "/tmp/b")


def test_cd_threads_project_root_to_runner(tmp_path: Path) -> None:
    # Ported from codex `-C/--cd <DIR>`: run the agent in a different directory.
    mock_runner = MagicMock()
    mock_runner.run = AsyncMock(return_value=None)
    with patch("autocode.cli.load_config", return_value=AutoCodeConfig()):
        with patch(
            "autocode.backend.headless_runner.HeadlessRunner",
            return_value=mock_runner,
        ) as runner_cls:
            result = runner.invoke(app, ["exec", "hi", "--json", "--cd", str(tmp_path)])
    assert result.exit_code == 0
    assert runner_cls.call_args.kwargs["project_root"] == tmp_path


def test_cd_nonexistent_dir_rejected() -> None:
    with patch("autocode.cli.load_config", return_value=AutoCodeConfig()):
        result = runner.invoke(
            app, ["exec", "hi", "--json", "--cd", "/no/such/dir/xyz123"]
        )
    assert result.exit_code != 0
    assert "directory" in result.output.lower() or "--cd" in result.output


def test_invalid_permission_mode_is_rejected() -> None:
    with patch("autocode.cli.load_config", return_value=AutoCodeConfig()):
        result = runner.invoke(
            app, ["exec", "hi", "--json", "--permission-mode", "nonsense"]
        )
    assert result.exit_code != 0
    assert "permission mode" in result.output.lower()


def test_existing_exec_behavior_unchanged_without_new_flags() -> None:
    mock_runner = MagicMock()
    mock_runner.run = AsyncMock(return_value=None)
    with patch("autocode.cli.load_config", return_value=AutoCodeConfig()):
        with patch(
            "autocode.backend.headless_runner.HeadlessRunner",
            return_value=mock_runner,
        ) as runner_cls:
            result = runner.invoke(app, ["exec", "hi", "--json"])
    assert result.exit_code == 0
    # Defaults: no mode override, no budget override, no prompt override.
    assert runner_cls.call_args.kwargs["permission_mode"] is None
    assert runner_cls.call_args.kwargs["max_budget_usd"] is None
    assert runner_cls.call_args.kwargs["system_prompt"] is None
    assert runner_cls.call_args.kwargs["append_system_prompt"] is None
    assert runner_cls.call_args.kwargs["add_dirs"] == ()


def test_runner_plan_mode_blocks_writes(tmp_path: Path) -> None:
    from autocode.backend.headless_runner import HeadlessRunner

    cfg = AutoCodeConfig()
    cfg.tui.session_db_path = str(tmp_path / "sessions.db")
    r = HeadlessRunner(config=cfg, project_root=tmp_path, permission_mode="plan")
    assert r._auto_approve is False
    assert r._permission_resolution.read_only is True


def test_runner_bypass_mode_auto_approves(tmp_path: Path) -> None:
    from autocode.backend.headless_runner import HeadlessRunner

    cfg = AutoCodeConfig()
    cfg.tui.session_db_path = str(tmp_path / "sessions2.db")
    r = HeadlessRunner(config=cfg, project_root=tmp_path, permission_mode="bypassPermissions")
    assert r._auto_approve is True


def test_runner_budget_override_takes_effect(tmp_path: Path) -> None:
    from autocode.backend.headless_runner import HeadlessRunner

    cfg = AutoCodeConfig()
    cfg.tui.session_db_path = str(tmp_path / "sessions3.db")
    cfg.agent.cost_limit_usd = None
    r = HeadlessRunner(config=cfg, project_root=tmp_path, max_budget_usd=2.25)
    assert r._effective_cost_limit_usd() == 2.25
    # Without an override, the config default is used.
    r2 = HeadlessRunner(config=cfg, project_root=tmp_path)
    assert r2._effective_cost_limit_usd() is None
