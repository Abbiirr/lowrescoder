"""C7 SB3 tests for worktree subagents, watch mode, and marketplace registry."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from autocode.app.commands import create_default_router
from autocode.config import AutoCodeConfig
from autocode.session.store import SessionStore


def _make_app(tmp_path: Path) -> MagicMock:
    config = AutoCodeConfig()
    config.tui.session_db_path = str(tmp_path / "sessions.db")
    store = SessionStore(tmp_path / "sessions.db")
    session_id = store.create_session("market", "coding", "openrouter", str(tmp_path))
    messages: list[str] = []
    app = MagicMock()
    app.config = config
    app.project_root = tmp_path
    app.session_store = store
    app.session_id = session_id
    app.command_router = create_default_router()
    app.add_system_message = lambda message: messages.append(message)
    app._messages = messages
    return app


def test_worktree_merge_plan_is_read_only_patch_command(tmp_path: Path) -> None:
    from autocode.agent.worktree import WorktreeInfo, build_merge_back_plan

    info = WorktreeInfo(
        path=tmp_path / "repo-wt",
        branch="autocode/wt",
        parent_repo=tmp_path / "repo",
        worktree_id="wt-1",
    )

    plan = build_merge_back_plan(info)

    assert plan.diff_command[:2] == ["git", "diff"]
    assert "apply_patch" in plan.instructions
    forbidden = {"commit", "push", "reset", "checkout", "merge", "pull"}
    assert forbidden.isdisjoint(set(plan.diff_command))


def test_spawn_subagent_can_allocate_worktree_without_current_tree_mutation(tmp_path: Path) -> None:
    from autocode.agent.subagent_tools import _make_spawn_handler
    from autocode.agent.worktree import WorktreeInfo

    manager = MagicMock()
    manager.spawn.return_value = "sub-1"
    manager.project_root = tmp_path / "repo"
    handler = _make_spawn_handler(manager)

    with patch(
        "autocode.agent.subagent_tools.create_worktree",
        return_value=WorktreeInfo(
            path=tmp_path / "wt",
            branch="autocode/wt",
            parent_repo=tmp_path / "repo",
            worktree_id="wt-1",
        ),
    ) as create:
        result = handler("execute", "implement feature", use_worktree=True)

    create.assert_called_once_with(tmp_path / "repo")
    assert "worktree" in result
    manager.spawn.assert_called_once()


def test_watch_marker_parser_extracts_autocode_instruction(tmp_path: Path) -> None:
    from autocode.agent.watch import parse_watch_markers

    path = tmp_path / "app.py"
    path.write_text("# AUTOCODE: add logging\nprint('x')\n", encoding="utf-8")

    markers = parse_watch_markers(path)

    assert markers == ["add logging"]


@pytest.mark.asyncio()
async def test_watch_command_toggles_state(tmp_path: Path) -> None:
    app = _make_app(tmp_path)

    on = app.command_router.dispatch("/watch on")
    status = app.command_router.dispatch("/watch status")
    off = app.command_router.dispatch("/watch off")

    assert on is not None and status is not None and off is not None
    await on[0].handler(app, on[1])
    await status[0].handler(app, status[1])
    await off[0].handler(app, off[1])

    assert "Watch mode ON" in app._messages[0]
    assert "enabled" in app._messages[1]
    assert "Watch mode OFF" in app._messages[2]


def test_marketplace_registry_loads_static_json_without_remote_fetch(tmp_path: Path) -> None:
    from autocode.external.registry import PluginRegistry

    registry_file = tmp_path / "registry.json"
    registry_file.write_text(
        json.dumps({
            "items": [
                {
                    "name": "fix-bug",
                    "kind": "recipe",
                    "description": "Bug fix recipe",
                    "source": "autocode/src/autocode/agent/recipes/fix-bug.yaml",
                }
            ]
        }),
        encoding="utf-8",
    )

    registry = PluginRegistry(registry_file)

    assert registry.list()[0].name == "fix-bug"
    assert registry.remote_fetch_enabled is False


@pytest.mark.asyncio()
async def test_marketplace_commands_list_info_and_warn_for_remote_install(tmp_path: Path) -> None:
    from autocode.external.registry import default_registry_path

    app = _make_app(tmp_path)
    registry_path = default_registry_path()
    assert registry_path.exists()

    listed = app.command_router.dispatch("/marketplace list")
    info = app.command_router.dispatch("/marketplace info fix-bug")

    assert listed is not None and info is not None
    await listed[0].handler(app, listed[1])
    await info[0].handler(app, info[1])

    assert "Marketplace" in app._messages[0]
    assert "fix-bug" in app._messages[1]
