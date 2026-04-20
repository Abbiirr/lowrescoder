"""Sprint verification tests.

Run after each sprint to validate end-to-end functionality.
Usage: uv run pytest tests/test_sprint_verify.py -v

These tests verify the EXIT CRITERIA for each sprint.
Mark completed sprints' tests to run by default;
future sprints are skipped until implemented.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from autocode.cli import app

runner = CliRunner()


# ============================================================
# Sprint 1: CLI + LLM Foundation
# ============================================================


class TestSprint1Config:
    """S1.1: Config system works end-to-end."""

    def test_config_loads_with_defaults(self) -> None:
        from autocode.config import AutoCodeConfig, load_config

        config = load_config(project_root=Path.cwd())
        assert isinstance(config, AutoCodeConfig)

    def test_default_provider_is_ollama(self) -> None:
        from autocode.config import AutoCodeConfig

        config = AutoCodeConfig()
        assert config.llm.provider == "ollama"

    def test_config_yaml_roundtrip(self, tmp_path: Path) -> None:
        from autocode.config import AutoCodeConfig, save_config

        config = AutoCodeConfig()
        config.llm.model = "test-roundtrip"
        path = save_config(config, tmp_path / "config.yaml")
        assert path.exists()
        assert "test-roundtrip" in path.read_text()

    def test_env_var_precedence(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        from autocode.config import load_config

        # Isolate from global config and .env overrides
        empty_dir = tmp_path / "_no_global"
        empty_dir.mkdir(exist_ok=True)
        monkeypatch.setattr(
            "autocode.config._resolve_global_config",
            lambda: (empty_dir, empty_dir / "config.yaml"),
        )
        monkeypatch.setenv("AUTOCODE_LLM_PROVIDER", "openrouter")
        monkeypatch.setenv("OPENROUTER_API_KEY", "fake-key")
        monkeypatch.delenv("AUTOCODE_LLM_API_BASE", raising=False)
        config = load_config(project_root=tmp_path)
        assert config.llm.provider == "openrouter"
        assert config.llm.api_base == "https://openrouter.ai/api/v1"

    def test_config_check_returns_list(self) -> None:
        from autocode.config import AutoCodeConfig, check_config

        config = AutoCodeConfig()
        config.layer3.enabled = False
        warnings = check_config(config)
        assert isinstance(warnings, list)


class TestSprint1CLI:
    """S1.2: CLI commands work."""

    def test_version_command(self) -> None:
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "autocode" in result.output

    def test_config_show_command(self) -> None:
        result = runner.invoke(app, ["config", "show"])
        assert result.exit_code == 0

    def test_config_check_command(self) -> None:
        result = runner.invoke(app, ["config", "check"])
        assert result.exit_code == 0

    def test_config_path_command(self) -> None:
        result = runner.invoke(app, ["config", "path"])
        assert result.exit_code == 0
        assert ".autocode" in result.output

    def test_config_set_validates_input(self) -> None:
        result = runner.invoke(app, ["config", "set", "bad"])
        assert result.exit_code == 1

    def test_edit_stub_responds(self) -> None:
        result = runner.invoke(app, ["edit", "test.py", "fix bug"])
        assert result.exit_code == 0
        assert "not yet implemented" in result.output

    def test_no_args_shows_help(self) -> None:
        result = runner.invoke(app, [])
        assert result.exit_code in (0, 2)


class TestSprint1LLMProvider:
    """S1.3: LLM provider abstraction works."""

    def test_create_provider_ollama(self) -> None:
        from autocode.config import AutoCodeConfig
        from autocode.layer4.llm import OllamaProvider, create_provider

        config = AutoCodeConfig()
        provider = create_provider(config)
        assert isinstance(provider, OllamaProvider)

    def test_create_provider_openrouter(self) -> None:
        from autocode.config import AutoCodeConfig
        from autocode.layer4.llm import OpenRouterProvider, create_provider

        config = AutoCodeConfig()
        config.llm.provider = "openrouter"
        provider = create_provider(config)
        assert isinstance(provider, OpenRouterProvider)

    def test_conversation_history(self) -> None:
        from autocode.layer4.llm import ConversationHistory

        h = ConversationHistory(system_prompt="test")
        h.add_user("hello")
        h.add_assistant("hi")
        msgs = h.get_messages()
        assert len(msgs) == 3
        assert msgs[0]["role"] == "system"
        assert msgs[1]["role"] == "user"
        assert msgs[2]["role"] == "assistant"

    def test_conversation_trim_preserves_pairs(self) -> None:
        from autocode.layer4.llm import ConversationHistory

        h = ConversationHistory(system_prompt="s")
        h.add_user("u" * 400)
        h.add_assistant("a" * 400)
        h.add_user("short")
        h.add_assistant("short")
        h.trim_to_budget(50)
        msgs = h.get_messages()
        assert msgs[0]["role"] == "system"
        # No orphan assistant without preceding user
        roles = [m["role"] for m in msgs[1:]]
        for i, role in enumerate(roles):
            if role == "assistant" and i > 0:
                assert roles[i - 1] == "user"

    def test_token_estimate(self) -> None:
        from autocode.layer4.llm import ConversationHistory

        h = ConversationHistory()
        h.add_user("a" * 400)
        assert h.token_estimate() == 100


class TestSprint1FileTools:
    """S1.4: File tools work with path safety."""

    def test_read_write_roundtrip(self, tmp_path: Path) -> None:
        from autocode.utils.file_tools import read_file, write_file

        write_file(tmp_path / "test.txt", "hello world")
        content = read_file(str(tmp_path / "test.txt"))
        assert content == "hello world"

    def test_read_line_range(self, tmp_path: Path) -> None:
        from autocode.utils.file_tools import read_file, write_file

        write_file(tmp_path / "lines.txt", "a\nb\nc\nd\n")
        content = read_file(str(tmp_path / "lines.txt"), start_line=2, end_line=3)
        assert "b" in content
        assert "c" in content
        assert "a" not in content

    def test_path_traversal_blocked(self, tmp_path: Path) -> None:
        from autocode.utils.file_tools import read_file

        (tmp_path / "sub").mkdir()
        (tmp_path / "secret.txt").write_text("secret")
        with pytest.raises(ValueError, match="escapes project root"):
            read_file(str(tmp_path / "secret.txt"), project_root=str(tmp_path / "sub"))

    def test_prefix_bypass_blocked(self, tmp_path: Path) -> None:
        from autocode.utils.file_tools import read_file

        repo = tmp_path / "repo"
        repo.mkdir()
        evil = tmp_path / "repo-evil"
        evil.mkdir()
        (evil / "steal.txt").write_text("stolen")
        with pytest.raises(ValueError, match="escapes project root"):
            read_file(str(evil / "steal.txt"), project_root=str(repo))

    def test_relative_path_resolves(self, tmp_path: Path) -> None:
        from autocode.utils.file_tools import read_file, write_file

        (tmp_path / "src").mkdir()
        write_file("src/test.txt", "content", project_root=str(tmp_path))
        result = read_file("src/test.txt", project_root=str(tmp_path))
        assert result == "content"

    def test_list_files(self, tmp_path: Path) -> None:
        from autocode.utils.file_tools import list_files

        (tmp_path / "a.py").write_text("a")
        (tmp_path / "b.txt").write_text("b")
        all_files = list_files(str(tmp_path))
        assert len(all_files) == 2
        py_files = list_files(str(tmp_path), pattern="*.py")
        assert len(py_files) == 1


class TestSprint1CoreTypes:
    """S1.5: Core types are defined correctly."""

    def test_request_type_enum(self) -> None:
        from autocode.core.types import RequestType

        assert len(RequestType) == 7
        assert RequestType.CHAT.value == "chat"
        assert RequestType.DETERMINISTIC_QUERY.value == "deterministic"

    def test_layer_result_enum(self) -> None:
        from autocode.core.types import LayerResult

        assert LayerResult.ESCALATE.value == "escalate"

    def test_request_dataclass(self) -> None:
        from autocode.core.types import Request, RequestType

        req = Request(raw_input="test", request_type=RequestType.CHAT)
        assert req.file_context is None
        assert req.conversation_history == []

    def test_response_dataclass(self) -> None:
        from autocode.core.types import Response

        resp = Response(content="hello", layer_used=4)
        assert resp.success is True
        assert resp.tokens_used == 0
        assert resp.files_modified == []

    def test_all_types_importable(self) -> None:
        from autocode.core.types import (
            CodeChunk,
            EditResult,
            FileRange,
            LayerResult,
            Request,
            RequestType,
            Response,
            SearchResult,
            Symbol,
        )

        # All types exist and are usable
        assert all(
            [
                RequestType,
                LayerResult,
                Request,
                Response,
                FileRange,
                Symbol,
                CodeChunk,
                SearchResult,
                EditResult,
            ]
        )


# ============================================================
# Sprint 2: Phase 2 — TUI Prototype
# ============================================================


class TestSprint2TUI:
    """S2.1: TUI app imports and constructs."""

    def test_tui_app_constructs(self, tmp_path: Path) -> None:
        from autocode.config import AutoCodeConfig
        from autocode.tui.app import AutoCodeApp

        config = AutoCodeConfig()
        config.tui.session_db_path = str(tmp_path / "test.db")
        app = AutoCodeApp(config=config)
        assert app is not None
        assert app.config is config

    def test_tui_widgets_importable(self) -> None:
        from autocode.tui.widgets import ChatView, InputBar, StatusBar

        assert ChatView is not None
        assert InputBar is not None
        assert StatusBar is not None


class TestSprint2Session:
    """S2.2: SessionStore creates DB and tables."""

    def test_session_store_creates_tables(self, tmp_path: Path) -> None:
        from autocode.session.store import SessionStore

        store = SessionStore(tmp_path / "test.db")
        # Tables should exist
        cursor = store._conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        assert "sessions" in tables
        assert "messages" in tables
        assert "tool_calls" in tables
        store.close()


class TestSprint2Tools:
    """S2.3: ToolRegistry registers 12 tools."""

    def test_twelve_tools_registered(self) -> None:
        from autocode.agent.tools import create_default_registry

        registry = create_default_registry()
        tools = registry.get_all()
        names = {t.name for t in tools}
        assert names == {
            "apply_patch",
            "ask_user",
            "edit_file",
            "find_definition",
            "find_references",
            "get_type_info",
            "git_diff",
            "git_log",
            "git_status",
            "list_files",
            "list_symbols",
            "lsp_find_references",
            "lsp_get_type",
            "lsp_goto_definition",
            "lsp_symbols",
            "read_file",
            "run_command",
            "search_code",
            "search_text",
            "semantic_search",
            "tool_search",
            "web_fetch",
            "todo_write", "todo_read", "glob_files", "grep_content",
            "write_file",
        }


class TestSprint2Agent:
    """S2.4: AgentLoop constructs with mock provider."""

    def test_agent_loop_constructs(self, tmp_path: Path) -> None:
        from unittest.mock import AsyncMock

        from autocode.agent.approval import ApprovalManager, ApprovalMode
        from autocode.agent.loop import AgentLoop
        from autocode.agent.tools import ToolRegistry
        from autocode.session.store import SessionStore

        store = SessionStore(tmp_path / "test.db")
        sid = store.create_session(title="T", model="m", provider="p")
        loop = AgentLoop(
            provider=AsyncMock(),
            tool_registry=ToolRegistry(),
            approval_manager=ApprovalManager(ApprovalMode.SUGGEST),
            session_store=store,
            session_id=sid,
        )
        assert loop.MAX_ITERATIONS == 1000
        store.close()


class TestSprint2Commands:
    """S2.5: All slash commands registered (16 with /tasks)."""

    def test_all_commands_registered(self) -> None:
        from autocode.tui.commands import create_default_router

        router = create_default_router()
        commands = router.get_all()
        names = {c.name for c in commands}
        expected = {
            "build",
            "checkpoint",
            "clear",
            "compact",
            "copy",
            "cost",
            "diff",
            "exit",
            "export",
            "freeze",
            "help",
            "index",
            "init",
            "loop",
            "memory",
            "mode",
            "model",
            "new",
            "plan",
            "provider",
            "research",
            "resume",
            "review",
            "sessions",
            "shell",
            "tasks",
            "thinking",
            "undo",
        }
        assert names == expected


