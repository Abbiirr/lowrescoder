"""Direct unit tests for host-independent backend application services."""

from __future__ import annotations

import asyncio
import contextlib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from autocode.agent.loop import AgentMode
from autocode.backend import services as backend_services
from autocode.config import DEFAULT_OLLAMA_API_BASE, DEFAULT_OLLAMA_MODEL
from autocode.session.store import SessionStore


@pytest.fixture
def config(tmp_path: Path) -> MagicMock:
    cfg = MagicMock()
    cfg.llm.model = DEFAULT_OLLAMA_MODEL
    cfg.llm.provider = "ollama"
    cfg.llm.api_base = DEFAULT_OLLAMA_API_BASE
    cfg.tui.approval_mode = "suggest"
    cfg.logging = MagicMock()
    cfg.model_dump.return_value = {
        "llm": {
            "model": DEFAULT_OLLAMA_MODEL,
            "provider": "ollama",
            "api_base": DEFAULT_OLLAMA_API_BASE,
        },
        "tui": {"approval_mode": "suggest"},
    }
    return cfg


@pytest.fixture
def session_store(tmp_path: Path) -> SessionStore:
    return SessionStore(str(tmp_path / "test_sessions.db"))


class TestSessionTransitions:
    @pytest.mark.asyncio
    async def test_create_session_transition_returns_new_session_metadata(
        self,
        config: MagicMock,
        session_store: SessionStore,
        tmp_path: Path,
    ) -> None:
        teardown = AsyncMock()
        log_dir = tmp_path / "logs" / "new-session"

        with patch(
            "autocode.backend.services.setup_session_logging",
            return_value=log_dir,
        ):
            transition = await backend_services.create_session_transition(
                title="Fresh Session",
                config=config,
                project_root=tmp_path,
                session_store=session_store,
                teardown_agent_resources=teardown,
            )

        teardown.assert_awaited_once()
        assert transition.title == "Fresh Session"
        assert transition.session_titled is True
        assert transition.session_log_dir == log_dir
        assert session_store.get_session(transition.session_id) is not None

    @pytest.mark.asyncio
    async def test_resume_session_transition_resolves_prefix_and_reuses_title(
        self,
        config: MagicMock,
        session_store: SessionStore,
        tmp_path: Path,
    ) -> None:
        existing_id = session_store.create_session(
            title="Existing Session",
            model=config.llm.model,
            provider=config.llm.provider,
            project_dir=str(tmp_path),
        )
        teardown = AsyncMock()
        log_dir = tmp_path / "logs" / "existing"

        with patch(
            "autocode.backend.services.setup_session_logging",
            return_value=log_dir,
        ):
            transition = await backend_services.resume_session_transition(
                session_id=existing_id[:8],
                config=config,
                session_store=session_store,
                teardown_agent_resources=teardown,
            )

        teardown.assert_awaited_once()
        assert transition.session_id == existing_id
        assert transition.title == "Existing Session"
        assert transition.session_titled is True
        assert transition.session_log_dir == log_dir

    @pytest.mark.asyncio
    async def test_resume_session_transition_rejects_missing_prefix(
        self,
        config: MagicMock,
        session_store: SessionStore,
    ) -> None:
        with pytest.raises(backend_services.BackendServiceError, match="Session ID is required"):
            await backend_services.resume_session_transition(
                session_id="   ",
                config=config,
                session_store=session_store,
                teardown_agent_resources=AsyncMock(),
            )


class TestCommandServices:
    @pytest.mark.asyncio
    async def test_execute_command_reports_status_change(self, config: MagicMock) -> None:
        async def change_model(context: object, args: str) -> None:
            context.config.llm.model = args

        router = MagicMock()
        router.dispatch.return_value = (SimpleNamespace(handler=change_model), "tools")
        context = SimpleNamespace(
            config=config,
            session_id="sess-1",
            session_store=MagicMock(),
            add_system_message=MagicMock(),
        )

        result = await backend_services.execute_command(
            cmd="/model tools",
            command_router=router,
            app_context=context,
            config=config,
        )

        assert result.payload == {"ok": True}
        assert result.status_changed is True
        assert config.llm.model == "tools"

    @pytest.mark.asyncio
    async def test_execute_command_unknown_command_emits_system_message(
        self,
        config: MagicMock,
    ) -> None:
        router = MagicMock()
        router.dispatch.return_value = None
        context = SimpleNamespace(
            config=config,
            session_id="sess-1",
            session_store=MagicMock(),
            add_system_message=MagicMock(),
        )

        result = await backend_services.execute_command(
            cmd="/unknown",
            command_router=router,
            app_context=context,
            config=config,
        )

        assert result.payload == {"ok": True}
        assert result.status_changed is False
        context.add_system_message.assert_called_once_with("Unknown command: /unknown")

    def test_build_command_list_payload_exposes_command_catalog(self) -> None:
        from autocode.app.commands import create_default_router

        payload = backend_services.build_command_list_payload(create_default_router())

        assert "commands" in payload
        assert any(command["name"] == "help" for command in payload["commands"])


class TestProjectionAndConfigServices:
    def test_build_task_state_payload_preserves_contract_shape(self) -> None:
        task = MagicMock()
        task.model_dump.return_value = {"id": "t1", "title": "Task", "status": "open"}
        task_store = MagicMock()
        task_store.list_tasks.return_value = [task]
        subagent_manager = MagicMock()
        subagent_manager.list_all.return_value = [
            {"id": "s1", "role": "worker", "status": "running"}
        ]

        payload = backend_services.build_task_state_payload(
            task_store=task_store,
            subagent_manager=subagent_manager,
        )

        assert payload == {
            "tasks": [{"id": "t1", "title": "Task", "status": "open"}],
            "subagents": [{"id": "s1", "role": "worker", "status": "running"}],
        }

    def test_build_model_list_payload_uses_shared_command_module(self, config: MagicMock) -> None:
        with patch(
            "autocode.app.commands._list_models",
            return_value=["coding", "tools"],
        ) as mock_list:
            payload = backend_services.build_model_list_payload(config)

        mock_list.assert_called_once_with("ollama", DEFAULT_OLLAMA_API_BASE)
        assert payload == {"models": ["coding", "tools"], "current": DEFAULT_OLLAMA_MODEL}

    def test_update_plan_mode_rejects_invalid_values(self) -> None:
        with pytest.raises(backend_services.BackendServiceError, match="Invalid mode"):
            backend_services.update_plan_mode(
                mode="broken",
                current_mode=AgentMode.NORMAL,
                agent_loop=None,
            )

    def test_update_config_validates_section_and_field(self, config: MagicMock) -> None:
        with pytest.raises(backend_services.BackendServiceError, match="section.field"):
            backend_services.update_config(config=config, key="invalid", value="value")

        with pytest.raises(backend_services.BackendServiceError, match="Unknown section"):
            backend_services.update_config(config=config, key="missing.field", value="value")


class TestSteerService:
    def test_inject_steer_requires_active_run(
        self,
        session_store: SessionStore,
        tmp_path: Path,
    ) -> None:
        session_id = session_store.create_session(
            title="Active",
            model=DEFAULT_OLLAMA_MODEL,
            provider="ollama",
            project_dir=str(tmp_path),
        )

        payload = backend_services.inject_steer(
            message="redirect",
            agent_task=None,
            agent_loop=None,
            session_store=session_store,
            session_id=session_id,
        )

        assert payload == {"error": "No active run to steer", "active": False}

    @pytest.mark.asyncio
    async def test_inject_steer_persists_message_when_run_is_active(
        self,
        session_store: SessionStore,
        tmp_path: Path,
    ) -> None:
        session_id = session_store.create_session(
            title="Active",
            model=DEFAULT_OLLAMA_MODEL,
            provider="ollama",
            project_dir=str(tmp_path),
        )
        loop = MagicMock()

        async def sleeper() -> None:
            await asyncio.sleep(0.1)

        task = asyncio.create_task(sleeper())
        try:
            payload = backend_services.inject_steer(
                message="try again",
                agent_task=task,
                agent_loop=loop,
                session_store=session_store,
                session_id=session_id,
            )
        finally:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

        messages = session_store.get_messages(session_id)
        assert payload == {"ok": True, "injected": True}
        loop.cancel.assert_called_once()
        assert any("[steer] try again" in message.content for message in messages)
