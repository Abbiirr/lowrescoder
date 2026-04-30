"""C7 SB1 tests for model split, nested rules, and session branching."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from autocode.agent.loop import AgentMode
from autocode.app.commands import create_default_router
from autocode.config import AutoCodeConfig, RoutingModelRateConfig
from autocode.session.store import SessionStore


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _make_app(tmp_path: Path) -> MagicMock:
    config = AutoCodeConfig()
    config.tui.session_db_path = str(tmp_path / "sessions.db")
    store = SessionStore(tmp_path / "sessions.db")
    session_id = store.create_session(
        title="SB1 test",
        model=config.llm.model,
        provider=config.llm.provider,
        project_dir=str(tmp_path),
    )
    messages: list[str] = []
    app = MagicMock()
    app.config = config
    app.project_root = tmp_path
    app.session_store = store
    app.session_id = session_id
    app.command_router = create_default_router()
    app._agent_mode = AgentMode.NORMAL
    app.add_system_message = lambda message: messages.append(message)
    app._messages = messages
    app.set_agent_mode = lambda mode: setattr(app, "_agent_mode", mode)
    return app


def test_layer45_architect_override_takes_precedence_over_auto_routing(tmp_path: Path) -> None:
    from autocode.backend.server import BackendServer

    config = AutoCodeConfig()
    config.tui.session_db_path = str(tmp_path / "sessions.db")
    config.layer1.enabled = False
    config.layer2.enabled = False
    config.layer3.enabled = False
    config.agent.architect_model = "architect-special"
    config.routing.model_rates = [
        RoutingModelRateConfig(
            provider="openrouter",
            model="frontier-router",
            tier="frontier",
            input_per_m=3.0,
            output_per_m=10.0,
        )
    ]
    server = BackendServer(config=config, project_root=tmp_path)
    server._agent_mode = AgentMode.PLANNING

    layer, _request_type, _forced = server._select_chat_layer(
        "plan a risky architecture migration"
    )

    assert layer == 4
    assert config.llm.model == "architect-special"
    assert server._last_provider_selection is not None
    assert "mode override" in server._last_provider_selection.reason


def test_layer45_editor_override_takes_precedence_over_auto_routing(tmp_path: Path) -> None:
    from autocode.backend.server import BackendServer

    config = AutoCodeConfig()
    config.tui.session_db_path = str(tmp_path / "sessions.db")
    config.layer1.enabled = False
    config.layer2.enabled = False
    config.layer3.enabled = False
    config.agent.editor_model = "editor-special"
    config.routing.model_rates = [
        RoutingModelRateConfig(
            provider="openrouter",
            model="mid-router",
            tier="mid",
            input_per_m=1.0,
            output_per_m=2.0,
        )
    ]
    server = BackendServer(config=config, project_root=tmp_path)
    server._agent_mode = AgentMode.BUILD

    server._select_chat_layer("fix the failing unit test")

    assert config.llm.model == "editor-special"
    assert server._last_provider_selection is not None
    assert "mode override" in server._last_provider_selection.reason


@pytest.mark.asyncio()
async def test_architect_and_editor_commands_set_mode_models(tmp_path: Path) -> None:
    app = _make_app(tmp_path)

    architect = app.command_router.dispatch("/architect gpt-5.5")
    editor = app.command_router.dispatch("/editor coding")

    assert architect is not None
    assert editor is not None
    await architect[0].handler(app, architect[1])
    await editor[0].handler(app, editor[1])

    assert app.config.agent.architect_model == "gpt-5.5"
    assert app.config.agent.editor_model == "coding"
    assert "Architect model" in app._messages[-2]
    assert "Editor model" in app._messages[-1]


def test_nested_agents_md_loads_parent_then_child_rules(tmp_path: Path) -> None:
    from autocode.layer2.rules import Provenance, RulesLoader

    child = tmp_path / "packages" / "api"
    _write(tmp_path / "AGENTS.md", "root rule\n")
    _write(child / "AGENTS.md", "api rule\n")

    result = RulesLoader().load_agents_nested(cwd=child, repo_root=tmp_path)

    assert result.text.index("root rule") < result.text.index("api rule")
    assert [source.kind for source in result.sources] == [
        Provenance.AGENTS_MD,
        Provenance.AGENTS_MD,
    ]


@pytest.mark.asyncio()
async def test_agents_reload_command_surfaces_nested_sources(tmp_path: Path) -> None:
    child = tmp_path / "packages" / "api"
    _write(tmp_path / "AGENTS.md", "root rule\n")
    _write(child / "AGENTS.md", "api rule\n")
    app = _make_app(tmp_path)
    app.project_root = child
    app.repo_root = tmp_path

    dispatched = app.command_router.dispatch("/agents reload")

    assert dispatched is not None
    await dispatched[0].handler(app, dispatched[1])
    assert "Reloaded 2 AGENTS.md source" in app._messages[-1]


def test_fork_session_records_parent_session_id(tmp_path: Path) -> None:
    from autocode.backend.services import fork_session

    store = SessionStore(tmp_path / "sessions.db")
    config = AutoCodeConfig()
    source = store.create_session(
        title="parent",
        model="coding",
        provider="openrouter",
        project_dir=str(tmp_path),
    )

    result = fork_session(
        session_store=store,
        source_session_id=source,
        config=config,
        project_root=tmp_path,
    )

    forked = store.get_session(result["new_session_id"])
    assert forked is not None
    assert forked.parent_session_id == source


@pytest.mark.asyncio()
async def test_fork_and_tree_commands_surface_branch_relationship(tmp_path: Path) -> None:
    app = _make_app(tmp_path)

    fork = app.command_router.dispatch("/fork")
    tree = app.command_router.dispatch("/tree")

    assert fork is not None
    assert tree is not None
    await fork[0].handler(app, fork[1])
    await tree[0].handler(app, tree[1])

    assert "Forked session" in app._messages[-2]
    assert app.session_id[:8] in app._messages[-1]


def test_rollout_replay_payload_preserves_message_and_tool_call_order(tmp_path: Path) -> None:
    from autocode.backend.services import build_rollout_replay_payload

    store = SessionStore(tmp_path / "sessions.db")
    session_id = store.create_session(
        title="replay",
        model="coding",
        provider="openrouter",
        project_dir=str(tmp_path),
    )
    first = store.add_message(session_id, "assistant", "step one")
    second = store.add_message(session_id, "assistant", "step two")
    store.add_tool_call(session_id, first, "call-1", "read_file", {"path": "a.py"})
    store.add_tool_call(session_id, second, "call-2", "write_file", {"path": "b.py"})

    payload = build_rollout_replay_payload(store, session_id)

    assert [item["content"] for item in payload["messages"]] == ["step one", "step two"]
    calls = [message["tool_calls"][0]["function"]["name"] for message in payload["messages"]]
    assert calls == ["read_file", "write_file"]
