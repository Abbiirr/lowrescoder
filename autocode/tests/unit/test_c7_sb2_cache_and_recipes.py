"""C7 SB2 tests for prompt-cache keepalive and recipe workflows."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from autocode.app.commands import create_default_router
from autocode.config import AutoCodeConfig
from autocode.session.store import SessionStore


def _make_app(tmp_path: Path) -> MagicMock:
    config = AutoCodeConfig()
    config.tui.session_db_path = str(tmp_path / "sessions.db")
    store = SessionStore(tmp_path / "sessions.db")
    session_id = store.create_session("recipes", "coding", "openrouter", str(tmp_path))
    messages: list[str] = []
    prompts: list[str] = []
    app = MagicMock()
    app.config = config
    app.project_root = tmp_path
    app.session_store = store
    app.session_id = session_id
    app.command_router = create_default_router()
    app.add_system_message = lambda message: messages.append(message)
    app.run_loop_prompt = AsyncMock(side_effect=lambda payload: prompts.append(payload))
    app._messages = messages
    app._prompts = prompts
    return app


def test_prompt_cache_keepalive_defaults_are_provider_gated() -> None:
    from autocode.agent.prompt_cache_keepalive import PromptCacheKeepaliveConfig

    config = PromptCacheKeepaliveConfig()

    assert config.enabled is True
    assert config.interval_seconds == 300
    assert config.should_enable_for_provider("openrouter / anthropic/claude-3.5-sonnet")
    assert not config.should_enable_for_provider("openrouter / openai/gpt-4")
    assert not config.should_enable_for_provider("ollama / qwen3:8b")


@pytest.mark.asyncio()
async def test_prompt_cache_keepalive_tick_calls_provider_and_records_savings() -> None:
    from autocode.agent.cost_dashboard import CostDashboard
    from autocode.agent.prompt_cache_keepalive import PromptCacheKeepalive

    provider = MagicMock()
    provider.model = "anthropic/claude-3.5-sonnet"
    provider.generate_with_tools = AsyncMock(
        return_value=MagicMock(
            usage={
                "prompt_tokens": 1_000,
                "cached_input_tokens": 9_000,
                "completion_tokens": 0,
            }
        )
    )
    dashboard = CostDashboard()
    keepalive = PromptCacheKeepalive(
        provider=provider,
        static_prompt="stable prefix",
        cost_dashboard=dashboard,
        provider_label="openrouter / anthropic/claude-3.5-sonnet",
    )

    await keepalive.tick()

    provider.generate_with_tools.assert_awaited_once()
    assert dashboard.total_cached_input_tokens == 9_000
    assert dashboard.estimated_cache_savings_usd > 0


def test_recipe_loader_discovers_project_and_global_recipes(tmp_path: Path) -> None:
    from autocode.agent.recipes import RecipeRegistry

    global_dir = tmp_path / "home" / ".autocode" / "recipes"
    project_dir = tmp_path / "repo" / ".autocode" / "recipes"
    global_dir.mkdir(parents=True)
    project_dir.mkdir(parents=True)
    (global_dir / "fix-bug.yaml").write_text(
        "name: fix-bug\ngoal: Fix a bug\nsteps:\n  - prompt: Inspect failure\n",
        encoding="utf-8",
    )
    (project_dir / "refactor.yaml").write_text(
        "name: refactor\ngoal: Refactor code\nsteps:\n  - task: Create plan\n  - prompt: Apply refactor\n",
        encoding="utf-8",
    )

    registry = RecipeRegistry(project_root=tmp_path / "repo", home=tmp_path / "home")

    names = [recipe.name for recipe in registry.list()]
    assert "fix-bug" in names
    assert "refactor" in names
    assert registry.get("refactor").steps[0].task == "Create plan"


def test_recipe_schema_rejects_empty_steps(tmp_path: Path) -> None:
    from autocode.agent.recipes import RecipeRegistry, RecipeValidationError

    recipe_dir = tmp_path / ".autocode" / "recipes"
    recipe_dir.mkdir(parents=True)
    (recipe_dir / "bad.yaml").write_text(
        "name: bad\ngoal: Missing useful work\nsteps: []\n",
        encoding="utf-8",
    )

    with pytest.raises(RecipeValidationError, match="at least one step"):
        RecipeRegistry(project_root=tmp_path, home=tmp_path / "home").list()


@pytest.mark.asyncio()
async def test_recipe_commands_list_and_run_recipe(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    recipe_dir = tmp_path / ".autocode" / "recipes"
    recipe_dir.mkdir(parents=True)
    (recipe_dir / "add-feature.yaml").write_text(
        (
            "name: add-feature\n"
            "goal: Add a small feature\n"
            "steps:\n"
            "  - task: Draft implementation plan\n"
            "  - prompt: Implement the smallest safe change\n"
        ),
        encoding="utf-8",
    )

    listed = app.command_router.dispatch("/recipe list")
    run = app.command_router.dispatch("/recipe run add-feature")

    assert listed is not None
    assert run is not None
    await listed[0].handler(app, listed[1])
    await run[0].handler(app, run[1])

    tasks = app.session_store.get_connection().execute("SELECT title FROM tasks").fetchall()
    assert "add-feature" in app._messages[0]
    assert tasks[0]["title"] == "Draft implementation plan"
    assert app._prompts == ["Implement the smallest safe change"]


def test_bundled_example_recipes_exist() -> None:
    from autocode.agent.recipes import bundled_recipe_dir

    names = {path.name for path in bundled_recipe_dir().glob("*.yaml")}

    assert {"refactor.yaml", "add-feature.yaml", "fix-bug.yaml"} <= names
