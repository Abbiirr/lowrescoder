"""Tests for slash command router and commands."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from autocode.agent.loop import AgentMode
from autocode.agent.pev import PlanStep, Verification
from autocode.app.commands import _handle_kairos, _handle_plan, create_default_router


async def _noop_handler(app: object, args: str) -> None:
    pass


class _FakePlanApp:
    def __init__(self) -> None:
        self.messages: list[str] = []
        self.prompts: list[str] = []
        self.verifications: list[str] = []

    def add_system_message(self, content: str) -> None:
        self.messages.append(content)

    async def run_loop_prompt(self, payload: str) -> None:
        self.prompts.append(payload)


class _FakeVerifiedPlanApp(_FakePlanApp):
    async def verify_pev_step(self, step: PlanStep, execution: object) -> Verification:
        self.verifications.append(step.id)
        if step.id == "execute":
            return Verification.fail(
                evidence="implementation did not satisfy the verifier",
                next_action="abort_plan",
            )
        return Verification.pass_(evidence=f"{step.id} verified")


class _FakeKairosApp:
    def __init__(self, audit_log_path: Path) -> None:
        self._kairos_audit_log_path = audit_log_path
        self.messages: list[str] = []

    def add_system_message(self, content: str) -> None:
        self.messages.append(content)


def test_tui_commands_is_compat_alias_to_shared_runtime() -> None:
    import autocode.app.commands as app_commands
    import autocode.tui.commands as tui_commands

    assert tui_commands is app_commands


@pytest.mark.asyncio
async def test_kairos_pulse_reads_audit_log(tmp_path: Path) -> None:
    from autocode.agent.proactive import KairosAuditLog

    audit_path = tmp_path / "kairos.jsonl"
    KairosAuditLog(audit_path).record_action(
        session_id="s1",
        action="kairos_tick_dry_run",
        metadata={"tick_id": "tick-1", "read_only": True},
    )
    app = _FakeKairosApp(audit_path)

    await _handle_kairos(app, "pulse")

    assert "KAIROS pulse" in app.messages[-1]
    assert "kairos_tick_dry_run: 1" in app.messages[-1]
    assert "tick=tick-1" in app.messages[-1]


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
        """All slash commands are registered."""
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
            "provider",
            "mode",
            "compact",
            "init",
            "shell",
            "copy",
            "freeze",
            "thinking",
            "verify",
            "clear",
            "index",
            "repomap",
            "tasks",
            "plan",
            "research",
            "build",
            "review",
            "architect",
            "editor",
            "agents",
            "fork",
            "tree",
            "recipe",
            "watch",
            "marketplace",
            "kairos",
            "memory",
            "checkpoint",
            "loop",
            "tui",
            "undo",
            "rollback",
            "diff",
            "cost",
            "export",
        }
        assert names == expected

    def test_kairos_command_dispatches(self) -> None:
        """The /kairos command is dispatched correctly."""
        router = create_default_router()
        result = router.dispatch("/kairos pulse")
        assert result is not None
        cmd, args = result
        assert cmd.name == "kairos"
        assert args == "pulse"

    def test_research_command_dispatches(self) -> None:
        """The /research command is dispatched correctly."""
        router = create_default_router()
        result = router.dispatch("/research on")
        assert result is not None
        cmd, args = result
        assert cmd.name == "research"
        assert args == "on"

    def test_research_alias_dispatches(self) -> None:
        """The /comprehend alias resolves to /research."""
        router = create_default_router()
        result = router.dispatch("/comprehend status")
        assert result is not None
        cmd, args = result
        assert cmd.name == "research"
        assert args == "status"

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

    def test_loop_command_dispatches(self) -> None:
        """The /loop command is dispatched correctly."""
        router = create_default_router()
        result = router.dispatch("/loop 10m summarize status")
        assert result is not None
        cmd, args = result
        assert cmd.name == "loop"
        assert args == "10m summarize status"

    @pytest.mark.asyncio
    async def test_plan_run_executes_manual_pev_steps(self) -> None:
        """The /plan run path drives manual PEV steps through run_loop_prompt."""
        app = _FakePlanApp()

        await _handle_plan(app, "run refactor the backend safely")

        assert len(app.prompts) == 4
        assert app.prompts[0].startswith("PEV manual plan step 1/4")
        assert "Goal: refactor the backend safely" in app.prompts[0]
        assert "Inspect the current state" in app.prompts[0]
        assert "PEV manual plan succeeded" in app.messages[-1]

    @pytest.mark.asyncio
    async def test_plan_run_uses_app_provided_verifier(self) -> None:
        """Manual PEV should fail when an app-provided verifier fails a step."""
        app = _FakeVerifiedPlanApp()

        await _handle_plan(app, "run refactor the backend safely")

        assert app.verifications == ["inspect", "execute"]
        assert len(app.prompts) == 2
        assert "PEV manual plan failed" in app.messages[-1]
        assert "implementation did not satisfy the verifier" in app.messages[-1]

    def test_provider_command_dispatches(self) -> None:
        """The /provider command is dispatched correctly."""
        router = create_default_router()
        result = router.dispatch("/provider openrouter")
        assert result is not None
        cmd, args = result
        assert cmd.name == "provider"
        assert args == "openrouter"

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

    def test_repomap_alias_dispatches(self) -> None:
        """The /map alias resolves to /repomap."""
        router = create_default_router()
        result = router.dispatch("/map")
        assert result is not None
        assert result[0].name == "repomap"


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
    app._agent_loop = MagicMock()
    app._session_stats = MagicMock()
    app._session_titled = True
    app._session_approved_tools = {"write_file"}

    messages: list[str] = []
    app.add_system_message = lambda msg: messages.append(msg)
    app._messages = messages  # expose for assertions

    app.approval_mode = config.tui.approval_mode
    app.shell_enabled = config.shell.enabled
    app.show_thinking = False
    app._agent_mode = AgentMode.NORMAL

    return app


class TestHandleExit:
    @pytest.mark.asyncio()
    async def test_exit_raises_eof(self, tmp_path: Path) -> None:
        """_handle_exit raises EOFError."""
        from autocode.app.commands import _handle_exit

        app = _make_mock_app(tmp_path)
        app.exit_app.side_effect = EOFError
        with pytest.raises(EOFError):
            await _handle_exit(app, "")


class TestHandleNew:
    @pytest.mark.asyncio()
    async def test_new_creates_session(self, tmp_path: Path) -> None:
        """_handle_new creates a new session with default title."""
        from autocode.app.commands import _handle_new

        app = _make_mock_app(tmp_path)
        old_id = app.session_id
        await _handle_new(app, "")
        # session_id should be updated
        assert app.session_id != old_id
        assert app._agent_loop is None
        assert app._session_stats is None
        assert app._session_titled is False
        assert app._session_approved_tools == set()
        assert "New session" in app._messages[-1]

    @pytest.mark.asyncio()
    async def test_new_with_custom_title(self, tmp_path: Path) -> None:
        """_handle_new uses custom title when provided."""
        from autocode.app.commands import _handle_new

        app = _make_mock_app(tmp_path)
        await _handle_new(app, "My Custom Title")
        assert app._agent_loop is None
        assert "My Custom Title" in app._messages[-1]


class TestHandleRollback:
    def _mock_checkpoint(self, checkpoint_id: str = "ckpt123") -> SimpleNamespace:
        return SimpleNamespace(
            id=checkpoint_id,
            label="pre write_file",
            kind="pre_tool",
            active_files='["src/app.py"]',
            parent_tool_call_id="tool123",
        )

    @pytest.mark.asyncio()
    async def test_rollback_restore_parses_restore_subcommand_before_lookup(
        self,
        tmp_path: Path,
    ) -> None:
        """`/rollback restore <id>` restores checkpoint <id>, not `restore <id>`."""
        from autocode.app.commands import _handle_rollback

        app = _make_mock_app(tmp_path)
        cp = self._mock_checkpoint("ckpt123")
        cp_store = MagicMock()
        cp_store.get_checkpoint.side_effect = lambda checkpoint_id: (
            cp if checkpoint_id == "ckpt123" else None
        )
        snap_dir = tmp_path / ".autocode" / "snapshots" / app.session_id / "tool123"
        snap_dir.mkdir(parents=True)

        with (
            patch("autocode.session.checkpoint_store.CheckpointStore", return_value=cp_store),
            patch("autocode.session.task_store.TaskStore", return_value=MagicMock()),
            patch("autocode.session.file_snapshot.restore_snapshot", return_value=["src/app.py"]),
            patch("pathlib.Path.home", return_value=tmp_path),
        ):
            await _handle_rollback(app, "restore ckpt123")

        assert cp_store.get_checkpoint.call_args_list[0].args == ("ckpt123",)
        cp_store.restore_checkpoint.assert_called_once()
        assert "Rolled back to checkpoint" in app._messages[-1]

    @pytest.mark.asyncio()
    async def test_rollback_checkpoint_id_previews_without_restore(
        self,
        tmp_path: Path,
    ) -> None:
        """`/rollback <id>` shows preview only and does not restore."""
        from autocode.app.commands import _handle_rollback

        app = _make_mock_app(tmp_path)
        cp_store = MagicMock()
        cp_store.get_checkpoint.return_value = self._mock_checkpoint("ckpt123")

        with patch("autocode.session.checkpoint_store.CheckpointStore", return_value=cp_store):
            await _handle_rollback(app, "ckpt123")

        cp_store.get_checkpoint.assert_called_with("ckpt123")
        cp_store.restore_checkpoint.assert_not_called()
        assert "Rollback preview" in app._messages[-1]
        assert "/rollback restore ckpt123" in app._messages[-1]

    @pytest.mark.asyncio()
    async def test_rollback_last_previews_latest_without_restore(
        self,
        tmp_path: Path,
    ) -> None:
        """`/rollback --last` previews latest checkpoint; restore remains explicit."""
        from autocode.app.commands import _handle_rollback

        app = _make_mock_app(tmp_path)
        cp = self._mock_checkpoint("latest123")
        cp_store = MagicMock()
        cp_store.list_per_tool_checkpoints.return_value = [cp]
        cp_store.get_checkpoint.return_value = cp

        with patch("autocode.session.checkpoint_store.CheckpointStore", return_value=cp_store):
            await _handle_rollback(app, "--last")

        cp_store.get_checkpoint.assert_called_with("latest123")
        cp_store.restore_checkpoint.assert_not_called()
        assert "Rollback preview" in app._messages[-1]
        assert "/rollback restore latest123" in app._messages[-1]

    @pytest.mark.asyncio()
    async def test_rollback_restore_without_id_errors_cleanly(self, tmp_path: Path) -> None:
        """`/rollback restore` with no ID returns a clean error."""
        from autocode.app.commands import _handle_rollback

        app = _make_mock_app(tmp_path)
        cp_store = MagicMock()
        cp_store.get_checkpoint.return_value = None

        with patch("autocode.session.checkpoint_store.CheckpointStore", return_value=cp_store):
            await _handle_rollback(app, "restore")

        cp_store.get_checkpoint.assert_not_called()
        cp_store.restore_checkpoint.assert_not_called()
        assert "Usage: `/rollback restore <id>`" in app._messages[-1]

    @pytest.mark.asyncio()
    async def test_rollback_without_args_lists_per_tool_checkpoints(
        self,
        tmp_path: Path,
    ) -> None:
        """`/rollback` lists recent per-tool checkpoints."""
        from autocode.app.commands import _handle_rollback

        app = _make_mock_app(tmp_path)
        cp_store = MagicMock()
        cp_store.list_per_tool_checkpoints.return_value = [
            self._mock_checkpoint("ckpt123"),
        ]

        with patch("autocode.session.checkpoint_store.CheckpointStore", return_value=cp_store):
            await _handle_rollback(app, "")

        cp_store.list_per_tool_checkpoints.assert_called_once()
        cp_store.restore_checkpoint.assert_not_called()
        assert "Per-tool checkpoints" in app._messages[-1]
        assert "`ckpt123`" in app._messages[-1]

    @pytest.mark.asyncio()
    async def test_rollback_restore_nonexistent_errors_without_restore_attempt(
        self,
        tmp_path: Path,
    ) -> None:
        """`/rollback restore <missing>` reports a clean miss and does not restore."""
        from autocode.app.commands import _handle_rollback

        app = _make_mock_app(tmp_path)
        cp_store = MagicMock()
        cp_store.get_checkpoint.return_value = None

        with patch("autocode.session.checkpoint_store.CheckpointStore", return_value=cp_store):
            await _handle_rollback(app, "restore missing123")

        cp_store.get_checkpoint.assert_called_once_with("missing123")
        cp_store.restore_checkpoint.assert_not_called()
        assert "Checkpoint not found: `missing123`" in app._messages[-1]


class TestHandleRepoMap:
    @pytest.mark.asyncio()
    async def test_repomap_command_generates_repo_map(self, tmp_path: Path) -> None:
        """`/repomap` builds and displays a ranked repo map."""
        from autocode.app.commands import _handle_repomap

        app = _make_mock_app(tmp_path)
        generator = MagicMock()
        generator.generate.return_value = "# Repo Map\n\n## main.py\n- function: `main` L1\n"

        with patch("autocode.layer2.repomap.RepoMapGenerator", return_value=generator):
            await _handle_repomap(app, "")

        generator.generate.assert_called_once_with(tmp_path)
        assert app._messages[-1].startswith("# Repo Map")


class TestHandleResume:
    @pytest.mark.asyncio()
    async def test_resume_resets_runtime_state(self, tmp_path: Path) -> None:
        """Resuming a session should clear stale loop/stats state."""
        from autocode.app.commands import _handle_resume

        app = _make_mock_app(tmp_path)
        resumed = app.session_store.create_session(
            title="Resume me",
            model="test-model",
            provider="ollama",
            project_dir=str(tmp_path),
        )

        await _handle_resume(app, resumed[:8])

        assert app.session_id == resumed
        assert app._agent_loop is None
        assert app._session_stats is None
        assert app._session_approved_tools == set()


class TestHandleHelp:
    @pytest.mark.asyncio()
    async def test_help_lists_all_commands(self, tmp_path: Path) -> None:
        """_handle_help lists all 14 commands."""
        from autocode.app.commands import _handle_help

        app = _make_mock_app(tmp_path)
        await _handle_help(app, "")
        output = app._messages[-1]
        assert "Available commands" in output
        # Check all 14 commands are mentioned
        for name in [
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
        ]:
            assert f"/{name}" in output


class TestHandleModel:
    @pytest.mark.asyncio()
    async def test_model_no_args_shows_current(self, tmp_path: Path) -> None:
        """_handle_model with no args shows current model and provider."""
        from autocode.app.commands import _handle_model

        app = _make_mock_app(tmp_path)
        with patch("autocode.app.commands._list_models", return_value=[]):
            await _handle_model(app, "")
        assert "Current model" in app._messages[-1]
        assert "provider" in app._messages[-1]

    @pytest.mark.asyncio()
    async def test_model_set_changes_config(self, tmp_path: Path) -> None:
        """_handle_model with arg changes model."""
        from autocode.app.commands import _handle_model

        app = _make_mock_app(tmp_path)
        await _handle_model(app, "llama3")
        assert app.config.llm.model == "llama3"
        assert "llama3" in app._messages[-1]

    @pytest.mark.asyncio()
    async def test_model_ollama_provider_shows_ollama_error(self, tmp_path: Path) -> None:
        """_handle_model with ollama provider shows Ollama-specific failure."""
        from autocode.app.commands import _handle_model

        app = _make_mock_app(tmp_path)
        app.config.llm.provider = "ollama"
        with patch("autocode.app.commands._list_models", return_value=[]):
            await _handle_model(app, "")
        assert "Ollama" in app._messages[-1]

    @pytest.mark.asyncio()
    async def test_model_openrouter_provider_shows_gateway_error(self, tmp_path: Path) -> None:
        """_handle_model with openrouter provider shows gateway-specific failure."""
        from autocode.app.commands import _handle_model

        app = _make_mock_app(tmp_path)
        app.config.llm.provider = "openrouter"
        app.config.llm.api_base = "http://localhost:4000/v1"
        with patch("autocode.app.commands._list_models", return_value=[]):
            await _handle_model(app, "")
        assert "gateway" in app._messages[-1]
        assert "localhost" in app._messages[-1]
        assert "Ollama" not in app._messages[-1]

    @pytest.mark.asyncio()
    async def test_model_with_available_models_shows_list(self, tmp_path: Path) -> None:
        """_handle_model with available models shows them with active marker."""
        from autocode.app.commands import _handle_model

        app = _make_mock_app(tmp_path)
        app.config.llm.provider = "openrouter"
        app.config.llm.model = "coding"
        with patch("autocode.app.commands._list_models", return_value=["coding", "tools", "fast"]):
            await _handle_model(app, "")
        assert "coding" in app._messages[-1]
        assert "(active)" in app._messages[-1]

    @pytest.mark.asyncio()
    async def test_model_large_catalog_truncation(self, tmp_path: Path) -> None:
        """_handle_model truncates large gateway catalogs with 'N more' note."""
        from autocode.app.commands import _handle_model

        app = _make_mock_app(tmp_path)
        app.config.llm.provider = "openrouter"
        app.config.llm.model = "coding"
        many_models = [f"model-{i}" for i in range(50)]
        many_models.append("coding")
        with patch("autocode.app.commands._list_models", return_value=many_models):
            await _handle_model(app, "")
        assert "more models available" in app._messages[-1]


class TestListModelHelpers:
    def test_list_models_ollama_delegates(self) -> None:
        """_list_models delegates to _list_ollama_models for ollama provider."""
        from autocode.app.commands import _list_models

        with patch("autocode.app.commands._list_ollama_models", return_value=["qwen3:8b"]):
            result = _list_models("ollama", "http://localhost:11434")
        assert result == ["qwen3:8b"]

    def test_list_models_openai_delegates(self) -> None:
        """_list_models delegates to _list_openai_models for non-ollama provider."""
        from autocode.app.commands import _list_models

        with patch("autocode.app.commands._list_openai_models", return_value=["coding"]):
            result = _list_models("openrouter", "http://localhost:4000/v1")
        assert result == ["coding"]

    def test_list_openai_models_success(self) -> None:
        """_list_openai_models parses OpenAI /models response."""
        from autocode.app.commands import _list_openai_models

        mock_data = b'{"data": [{"id": "coding"}, {"id": "tools"}, {"id": "fast"}]}'
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = mock_data
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_resp
            result = _list_openai_models("http://localhost:4000/v1")
        assert result == ["coding", "fast", "tools"]

    def test_list_openai_models_uses_gateway_auth_headers(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """_list_openai_models includes gateway auth when available."""
        from autocode.app.commands import _list_openai_models

        monkeypatch.setenv("LITELLM_API_KEY", "test-gateway-key")
        captured_request = None

        def _fake_urlopen(req: object, timeout: int = 5) -> MagicMock:
            nonlocal captured_request
            captured_request = req
            mock_resp = MagicMock()
            mock_resp.read.return_value = b'{"data": [{"id": "coding"}]}'
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            return mock_resp

        with patch("urllib.request.urlopen", side_effect=_fake_urlopen):
            result = _list_openai_models("http://localhost:4000/v1")

        assert result == ["coding"]
        assert captured_request is not None
        assert captured_request.headers["Authorization"] == "Bearer test-gateway-key"

    def test_list_openai_models_failure_returns_empty(self) -> None:
        """_list_openai_models returns empty list on failure."""
        from autocode.app.commands import _list_openai_models

        with patch("urllib.request.urlopen", side_effect=Exception("connection refused")):
            result = _list_openai_models("http://localhost:4000/v1")
        assert result == []

    def test_prioritize_models_small_catalog(self) -> None:
        """_prioritize_models returns all models when under limit."""
        from autocode.app.commands import _prioritize_models

        displayed, remaining = _prioritize_models(["a", "b", "c"], "b")
        assert remaining == 0
        assert displayed[0] == "b"

    def test_prioritize_models_large_catalog(self) -> None:
        """_prioritize_models truncates large catalogs and reports remainder."""
        from autocode.app.commands import _GATEWAY_DISPLAY_LIMIT, _prioritize_models

        models = ["coding"] + [f"model-{i}" for i in range(_GATEWAY_DISPLAY_LIMIT + 10)]
        displayed, remaining = _prioritize_models(models, "coding")
        assert remaining > 0
        assert displayed[0] == "coding"
        assert len(displayed) <= _GATEWAY_DISPLAY_LIMIT

    def test_prioritize_models_aliases_before_rest(self) -> None:
        """_prioritize_models puts known aliases before generic models."""
        from autocode.app.commands import _prioritize_models

        models = ["zzz-generic", "coding", "aaa-generic", "tools"]
        displayed, remaining = _prioritize_models(models, "not-in-list")
        assert remaining == 0
        coding_idx = displayed.index("coding")
        tools_idx = displayed.index("tools")
        zzz_idx = displayed.index("zzz-generic")
        assert coding_idx < zzz_idx
        assert tools_idx < zzz_idx


class TestHandleMode:
    @pytest.mark.asyncio()
    async def test_mode_no_args_shows_current(self, tmp_path: Path) -> None:
        """_handle_mode with no args shows current mode."""
        from autocode.app.commands import _handle_mode

        app = _make_mock_app(tmp_path)
        await _handle_mode(app, "")
        assert "Current mode" in app._messages[-1]

    @pytest.mark.asyncio()
    async def test_mode_set_valid(self, tmp_path: Path) -> None:
        """_handle_mode sets valid mode."""
        from autocode.app.commands import _handle_mode

        app = _make_mock_app(tmp_path)
        await _handle_mode(app, "auto")
        assert app.approval_mode == "auto"
        assert "auto" in app._messages[-1]

    @pytest.mark.asyncio()
    async def test_mode_set_invalid_rejected(self, tmp_path: Path) -> None:
        """_handle_mode rejects invalid mode."""
        from autocode.app.commands import _handle_mode

        app = _make_mock_app(tmp_path)
        await _handle_mode(app, "invalid-mode")
        assert "Invalid mode" in app._messages[-1]


class TestHandleTui:
    @pytest.mark.asyncio()
    async def test_tui_no_args_shows_current_default(self, tmp_path: Path) -> None:
        """_handle_tui with no args shows current saved launch mode."""
        from autocode.app.commands import _handle_tui

        app = _make_mock_app(tmp_path)
        await _handle_tui(app, "")
        assert "Current TUI launch mode" in app._messages[-1]
        assert "inline" in app._messages[-1]

    @pytest.mark.asyncio()
    async def test_tui_sets_altscreen_and_persists_config(self, tmp_path: Path) -> None:
        """_handle_tui persists altscreen as the next-launch default."""
        from autocode.app.commands import _handle_tui

        app = _make_mock_app(tmp_path)
        with patch("autocode.app.commands.save_config") as mock_save:
            await _handle_tui(app, "altscreen")

        assert app.config.tui.alternate_screen is True
        mock_save.assert_called_once_with(app.config)
        assert "altscreen" in app._messages[-1]

    @pytest.mark.asyncio()
    async def test_tui_sets_inline_and_persists_config(self, tmp_path: Path) -> None:
        """_handle_tui persists inline as the next-launch default."""
        from autocode.app.commands import _handle_tui

        app = _make_mock_app(tmp_path)
        app.config.tui.alternate_screen = True
        with patch("autocode.app.commands.save_config") as mock_save:
            await _handle_tui(app, "inline")

        assert app.config.tui.alternate_screen is False
        mock_save.assert_called_once_with(app.config)
        assert "inline" in app._messages[-1]

    @pytest.mark.asyncio()
    async def test_tui_rejects_invalid_mode(self, tmp_path: Path) -> None:
        """_handle_tui rejects unsupported launch modes."""
        from autocode.app.commands import _handle_tui

        app = _make_mock_app(tmp_path)
        await _handle_tui(app, "fullscreen")
        assert "Invalid TUI mode" in app._messages[-1]


class TestHandleProvider:
    @pytest.mark.asyncio()
    async def test_provider_no_args_shows_current(self, tmp_path: Path) -> None:
        """_handle_provider with no args shows current provider."""
        from autocode.app.commands import _handle_provider

        app = _make_mock_app(tmp_path)
        app.config.llm.provider = "openrouter"
        await _handle_provider(app, "")
        assert "Current provider" in app._messages[-1]
        assert "openrouter" in app._messages[-1]

    @pytest.mark.asyncio()
    async def test_provider_list_shows_supported_values(self, tmp_path: Path) -> None:
        """_handle_provider list shows supported providers."""
        from autocode.app.commands import _handle_provider

        app = _make_mock_app(tmp_path)
        await _handle_provider(app, "list")
        assert "Available providers" in app._messages[-1]
        assert "ollama" in app._messages[-1]
        assert "openrouter" in app._messages[-1]

    @pytest.mark.asyncio()
    async def test_provider_set_changes_config(self, tmp_path: Path) -> None:
        """_handle_provider switches the configured provider."""
        from autocode.app.commands import _handle_provider

        app = _make_mock_app(tmp_path)
        app.config.llm.provider = "ollama"
        await _handle_provider(app, "openrouter")
        assert app.config.llm.provider == "openrouter"
        assert "Switched provider to: openrouter" in app._messages[-1]

    @pytest.mark.asyncio()
    async def test_provider_rejects_unknown_value(self, tmp_path: Path) -> None:
        """_handle_provider rejects unsupported providers."""
        from autocode.app.commands import _handle_provider

        app = _make_mock_app(tmp_path)
        await _handle_provider(app, "definitely-not-real")
        assert "Invalid provider" in app._messages[-1]


class TestHandleCompact:
    @pytest.mark.asyncio()
    async def test_compact_few_messages_early_return(self, tmp_path: Path) -> None:
        """_handle_compact returns early with <4 messages."""
        from autocode.app.commands import _handle_compact

        app = _make_mock_app(tmp_path)
        # Add only 2 messages
        app.session_store.add_message(app.session_id, "user", "hello")
        app.session_store.add_message(app.session_id, "assistant", "hi")
        await _handle_compact(app, "")
        assert "Not enough" in app._messages[-1]

    @pytest.mark.asyncio()
    async def test_compact_enough_messages(self, tmp_path: Path) -> None:
        """_handle_compact compacts when enough messages exist."""
        from autocode.app.commands import _handle_compact

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
        from autocode.app.commands import _handle_shell

        app = _make_mock_app(tmp_path)
        await _handle_shell(app, "on")
        assert app.shell_enabled is True
        assert "enabled" in app._messages[-1]

    @pytest.mark.asyncio()
    async def test_shell_off(self, tmp_path: Path) -> None:
        """_handle_shell disables shell."""
        from autocode.app.commands import _handle_shell

        app = _make_mock_app(tmp_path)
        await _handle_shell(app, "off")
        assert app.shell_enabled is False
        assert "disabled" in app._messages[-1]

    @pytest.mark.asyncio()
    async def test_shell_no_args_shows_status(self, tmp_path: Path) -> None:
        """_handle_shell with no args shows status."""
        from autocode.app.commands import _handle_shell

        app = _make_mock_app(tmp_path)
        await _handle_shell(app, "")
        output = app._messages[-1]
        assert "enabled" in output or "disabled" in output


class TestHandleCopy:
    @pytest.mark.asyncio()
    async def test_copy_no_args_copies_last(self, tmp_path: Path) -> None:
        """_handle_copy with no args copies last assistant message."""
        from autocode.app.commands import _handle_copy

        app = _make_mock_app(tmp_path)
        app.session_store.add_message(app.session_id, "assistant", "response text")
        app.copy_to_clipboard = MagicMock(return_value=True)
        await _handle_copy(app, "")
        app.copy_to_clipboard.assert_called_once_with("response text")
        assert "Copied" in app._messages[-1]

    @pytest.mark.asyncio()
    async def test_copy_n(self, tmp_path: Path) -> None:
        """_handle_copy N copies Nth-last assistant message."""
        from autocode.app.commands import _handle_copy

        app = _make_mock_app(tmp_path)
        app.session_store.add_message(app.session_id, "assistant", "first")
        app.session_store.add_message(app.session_id, "assistant", "second")
        app.copy_to_clipboard = MagicMock(return_value=True)
        await _handle_copy(app, "2")
        app.copy_to_clipboard.assert_called_once_with("first")

    @pytest.mark.asyncio()
    async def test_copy_all(self, tmp_path: Path) -> None:
        """_handle_copy all copies all messages."""
        from autocode.app.commands import _handle_copy

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
        from autocode.app.commands import _handle_copy

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
        from autocode.app.commands import _handle_copy

        app = _make_mock_app(tmp_path)
        await _handle_copy(app, "")
        assert "No assistant messages" in app._messages[-1]

    @pytest.mark.asyncio()
    async def test_copy_clipboard_fail(self, tmp_path: Path) -> None:
        """_handle_copy shows fallback when clipboard fails."""
        from autocode.app.commands import _handle_copy

        app = _make_mock_app(tmp_path)
        app.session_store.add_message(app.session_id, "assistant", "response")
        app.copy_to_clipboard = MagicMock(return_value=False)
        await _handle_copy(app, "")
        assert "Clipboard unavailable" in app._messages[-1]


class TestHandleThinking:
    @pytest.mark.asyncio()
    async def test_thinking_toggles(self, tmp_path: Path) -> None:
        """_handle_thinking toggles show_thinking on/off."""
        from autocode.app.commands import _handle_thinking

        app = _make_mock_app(tmp_path)
        assert app.show_thinking is False
        await _handle_thinking(app, "")
        assert app.show_thinking is True
        assert "on" in app._messages[-1]

    @pytest.mark.asyncio()
    async def test_thinking_accepts_explicit_on_off(self, tmp_path: Path) -> None:
        """_handle_thinking supports deterministic /thinking on|off."""
        from autocode.app.commands import _handle_thinking

        app = _make_mock_app(tmp_path)
        app.show_thinking = True

        await _handle_thinking(app, "off")
        assert app.show_thinking is False
        assert "off" in app._messages[-1]
        await _handle_thinking(app, "off")
        assert app.show_thinking is False

        await _handle_thinking(app, "on")
        assert app.show_thinking is True
        assert "on" in app._messages[-1]
        await _handle_thinking(app, "on")
        assert app.show_thinking is True


class TestHandleClear:
    @pytest.mark.asyncio()
    async def test_clear_writes_ansi_and_message(self, tmp_path: Path) -> None:
        """_handle_clear writes ANSI clear + confirmation."""
        from autocode.app.commands import _handle_clear

        app = _make_mock_app(tmp_path)
        with patch("sys.stdout"):
            await _handle_clear(app, "")
        assert "cleared" in app._messages[-1].lower()


class TestHandleFreeze:
    @pytest.mark.asyncio()
    async def test_freeze_inline_mode(self, tmp_path: Path) -> None:
        """_handle_freeze in inline mode shows 'not needed' message."""
        from autocode.app.commands import _handle_freeze

        app = _make_mock_app(tmp_path)
        # MagicMock doesn't have query_one by default (no hasattr match)
        del app.query_one
        await _handle_freeze(app, "")
        assert "not needed" in app._messages[-1].lower()


class TestHandleCost:
    @pytest.mark.asyncio()
    async def test_handle_cost_default_mode_displays_real_numbers(
        self,
        tmp_path: Path,
    ) -> None:
        """Default /cost uses CostDashboard totals, not message character estimates."""
        from autocode.agent.cost_dashboard import CostDashboard
        from autocode.app.commands import _handle_cost

        app = _make_mock_app(tmp_path)
        app.config.llm.provider = "openrouter"
        app.config.llm.model = "coding"
        dashboard = CostDashboard()
        dashboard.record(
            "primary",
            "session",
            "external",
            tokens_in=1_722,
            cached_input_tokens=8_512,
            tokens_out=5_389,
            provider_model="openrouter / coding",
        )
        app._cost_dashboard = dashboard
        for idx in range(4):
            app.session_store.add_message(app.session_id, "user", f"turn {idx}")

        await _handle_cost(app, "")

        output = app._messages[-1]
        assert "Session: $0.02 · 15,623 tokens · 4 turns" in output
        assert "Input:  10,234 (8,512 cached, 83% hit) · $0.0077" in output
        assert "Output: 5,389 · $0.0162" in output
        assert "Provider: openrouter / coding" in output

    @pytest.mark.asyncio()
    async def test_handle_cost_default_mode_skips_input_output_when_zero(
        self,
        tmp_path: Path,
    ) -> None:
        """Fresh sessions show a compact zero-state without empty input/output rows."""
        from autocode.agent.cost_dashboard import CostDashboard
        from autocode.app.commands import _handle_cost

        app = _make_mock_app(tmp_path)
        app._cost_dashboard = CostDashboard()

        await _handle_cost(app, "")

        output = app._messages[-1]
        assert "Session: $0.00 · 0 tokens · 0 turns" in output
        assert "Input:" not in output
        assert "Output:" not in output

    @pytest.mark.asyncio()
    async def test_handle_cost_default_mode_drops_cached_segment_when_zero(
        self,
        tmp_path: Path,
    ) -> None:
        """Non-cache providers do not show a misleading cached-token segment."""
        from autocode.agent.cost_dashboard import CostDashboard
        from autocode.app.commands import _handle_cost

        app = _make_mock_app(tmp_path)
        app.config.llm.provider = "ollama"
        app.config.llm.model = "qwen-7b"
        dashboard = CostDashboard()
        dashboard.record(
            "primary",
            "session",
            "l4",
            tokens_in=3_000,
            tokens_out=1_200,
            provider_model="ollama / qwen-7b",
        )
        app._cost_dashboard = dashboard
        app.session_store.add_message(app.session_id, "user", "turn")
        app.session_store.add_message(app.session_id, "user", "turn")

        await _handle_cost(app, "")

        output = app._messages[-1]
        assert "Input:  3,000 · $0.0000" in output
        assert "cached" not in output
        assert "Provider: ollama / qwen-7b" in output

    @pytest.mark.asyncio()
    async def test_handle_cost_detail_mode_renders_per_model_breakdown(
        self,
        tmp_path: Path,
    ) -> None:
        """/cost --detail renders per-provider/model totals and cache savings."""
        from autocode.agent.cost_dashboard import CostDashboard
        from autocode.app.commands import _handle_cost

        app = _make_mock_app(tmp_path)
        dashboard = CostDashboard()
        dashboard.record(
            "primary",
            "session",
            "external",
            tokens_in=1_722,
            cached_input_tokens=8_512,
            tokens_out=5_389,
            provider_model="openrouter / coding",
        )
        dashboard.record(
            "primary",
            "session",
            "external",
            tokens_in=500,
            tokens_out=923,
            provider_model="openrouter / swebench",
        )
        app._cost_dashboard = dashboard

        await _handle_cost(app, "--detail")

        output = app._messages[-1]
        assert "Per-model:" in output
        assert "openrouter / coding:" in output
        assert "openrouter / swebench:" in output
        assert "Cache: 8,512 cached / 10,734 input (79% hit) - saved ~$0.02" in output

    @pytest.mark.asyncio()
    async def test_handle_cost_detail_mode_renders_cache_writes_and_reasoning(
        self,
        tmp_path: Path,
    ) -> None:
        """Tier 1.3 /cost detail surfaces cache writes and reasoning tokens."""
        from autocode.agent.cost_dashboard import CostDashboard
        from autocode.agent.token_tracker import TokenTracker
        from autocode.app.commands import _handle_cost

        app = _make_mock_app(tmp_path)
        dashboard = CostDashboard()
        tracker = TokenTracker(cost_dashboard=dashboard)
        tracker.record(
            prompt_tokens=10_000,
            completion_tokens=2_000,
            provider="openrouter / anthropic/claude",
            cached_input_tokens=6_000,
            cache_creation_tokens=1_000,
            reasoning_tokens=500,
        )
        app._session_stats.token_tracker = tracker

        await _handle_cost(app, "--detail")

        output = app._messages[-1]
        assert "cache writes: 1,000" in output
        assert "reasoning: 500" in output
        assert "effective input multiplier: 0.585x" in output

    @pytest.mark.asyncio()
    async def test_handle_cost_renders_threshold_when_set(self, tmp_path: Path) -> None:
        """Cost limit display is shown only when configured."""
        from autocode.agent.cost_dashboard import CostDashboard
        from autocode.app.commands import _handle_cost

        app = _make_mock_app(tmp_path)
        app.config.agent.cost_limit_usd = 0.5
        dashboard = CostDashboard()
        dashboard.record(
            "primary",
            "session",
            "external",
            tokens_in=1_722,
            cached_input_tokens=8_512,
            tokens_out=5_389,
            provider_model="openrouter / coding",
        )
        app._cost_dashboard = dashboard

        await _handle_cost(app, "")

        assert "Limit:   $0.50 (5% used)" in app._messages[-1]

    @pytest.mark.asyncio()
    async def test_handle_cost_unknown_arg_returns_friendly_error(
        self,
        tmp_path: Path,
    ) -> None:
        """Unknown /cost arguments explain the supported forms."""
        from autocode.app.commands import _handle_cost

        app = _make_mock_app(tmp_path)

        await _handle_cost(app, "--verbose")

        assert app._messages[-1] == (
            "Unknown /cost option: '--verbose'. Use /cost or /cost --detail."
        )


class _LoopTestApp:
    def __init__(self, tmp_path: Path) -> None:
        self.session_store = _make_mock_app(tmp_path).session_store
        self.session_id = self.session_store.create_session(
            title="Loop session",
            model="test-model",
            provider="ollama",
            project_dir=str(tmp_path),
        )
        from autocode.config import AutoCodeConfig

        self.config = AutoCodeConfig()
        self.project_root = tmp_path
        self.command_router = create_default_router()
        self.messages: list[str] = []
        self.prompt_runs: list[str] = []
        self.command_runs: list[str] = []

    def add_system_message(self, content: str) -> None:
        self.messages.append(content)

    async def run_loop_prompt(self, payload: str) -> None:
        self.prompt_runs.append(payload)

    async def run_loop_command(self, payload: str) -> None:
        self.command_runs.append(payload)


class TestHandleLoop:
    @pytest.mark.asyncio()
    async def test_loop_create_list_cancel(self, tmp_path: Path) -> None:
        """/loop supports create/list/cancel lifecycle."""
        from autocode.app.commands import _handle_loop

        app = _LoopTestApp(tmp_path)
        await _handle_loop(app, "10m status")
        assert "Started loop #1" in app.messages[-1]

        await _handle_loop(app, "list")
        assert "#1" in app.messages[-1]
        assert "status" in app.messages[-1]

        await _handle_loop(app, "cancel 1")
        assert "Cancelled loop #1" in app.messages[-1]

    @pytest.mark.asyncio()
    async def test_loop_routes_prompt_and_command_payloads(self, tmp_path: Path) -> None:
        """Loop payload routing uses command path for slash and prompt path otherwise."""
        from autocode.app.commands import _execute_loop_payload

        app = _LoopTestApp(tmp_path)
        await _execute_loop_payload(app, "/help")
        await _execute_loop_payload(app, "summarize changes")

        assert app.command_runs == ["/help"]
        assert app.prompt_runs == ["summarize changes"]


class TestHandleResearch:
    @pytest.mark.asyncio()
    async def test_research_on_sets_agent_mode(self, tmp_path: Path) -> None:
        """Research mode should switch the app into read-only comprehension mode."""
        from autocode.app.commands import _handle_research

        app = _make_mock_app(tmp_path)
        recorded: list[AgentMode] = []

        def set_agent_mode(mode: AgentMode) -> None:
            recorded.append(mode)
            app._agent_mode = mode

        app.set_agent_mode = set_agent_mode

        await _handle_research(app, "on")

        assert recorded == [AgentMode.RESEARCH]
        assert "Research mode ON" in app._messages[-1]

    @pytest.mark.asyncio()
    async def test_research_status_reports_current_mode(self, tmp_path: Path) -> None:
        """Research status should display the current persisted agent mode."""
        from autocode.app.commands import _handle_research

        app = _make_mock_app(tmp_path)
        app._agent_mode = AgentMode.RESEARCH

        await _handle_research(app, "status")

        assert "research" in app._messages[-1].lower()


class TestHandleInit:
    @pytest.mark.asyncio()
    async def test_init_creates_memory(self, tmp_path: Path) -> None:
        """_handle_init creates memory.md."""
        from autocode.app.commands import _handle_init

        app = _make_mock_app(tmp_path)
        await _handle_init(app, "")
        memory_file = tmp_path / ".autocode" / "memory.md"
        assert memory_file.exists()
        assert "Created" in app._messages[-1]

    @pytest.mark.asyncio()
    async def test_init_already_exists(self, tmp_path: Path) -> None:
        """_handle_init reports if memory.md already exists."""
        from autocode.app.commands import _handle_init

        app = _make_mock_app(tmp_path)
        memory_dir = tmp_path / ".autocode"
        memory_dir.mkdir(parents=True)
        (memory_dir / "memory.md").write_text("existing")
        await _handle_init(app, "")
        assert "already exists" in app._messages[-1]

    @pytest.mark.asyncio()
    async def test_init_reads_key_files(self, tmp_path: Path) -> None:
        """_handle_init includes key files in memory."""
        from autocode.app.commands import _handle_init

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
        from autocode.app.commands import _handle_resume
        from autocode.config import AutoCodeConfig
        from autocode.session.store import SessionStore

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
        from autocode.app.commands import _handle_sessions
        from autocode.config import AutoCodeConfig
        from autocode.session.store import SessionStore

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
