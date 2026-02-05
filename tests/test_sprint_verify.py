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

from hybridcoder.cli import app

runner = CliRunner()


# ============================================================
# Sprint 1: CLI + LLM Foundation
# ============================================================


class TestSprint1Config:
    """S1.1: Config system works end-to-end."""

    def test_config_loads_with_defaults(self) -> None:
        from hybridcoder.config import HybridCoderConfig, load_config

        config = load_config(project_root=Path.cwd())
        assert isinstance(config, HybridCoderConfig)

    def test_default_provider_is_ollama(self) -> None:
        from hybridcoder.config import HybridCoderConfig

        config = HybridCoderConfig()
        assert config.llm.provider == "ollama"

    def test_config_yaml_roundtrip(self, tmp_path: Path) -> None:
        from hybridcoder.config import HybridCoderConfig, save_config

        config = HybridCoderConfig()
        config.llm.model = "test-roundtrip"
        path = save_config(config, tmp_path / "config.yaml")
        assert path.exists()
        assert "test-roundtrip" in path.read_text()

    def test_env_var_precedence(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        from hybridcoder.config import load_config

        monkeypatch.setenv("HYBRIDCODER_LLM_PROVIDER", "openrouter")
        monkeypatch.setenv("OPENROUTER_API_KEY", "fake-key")
        config = load_config(project_root=tmp_path)
        assert config.llm.provider == "openrouter"
        assert config.llm.api_base == "https://openrouter.ai/api/v1"

    def test_config_check_returns_list(self) -> None:
        from hybridcoder.config import HybridCoderConfig, check_config

        config = HybridCoderConfig()
        config.layer3.enabled = False
        warnings = check_config(config)
        assert isinstance(warnings, list)


class TestSprint1CLI:
    """S1.2: CLI commands work."""

    def test_version_command(self) -> None:
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "hybridcoder" in result.output

    def test_config_show_command(self) -> None:
        result = runner.invoke(app, ["config", "show"])
        assert result.exit_code == 0

    def test_config_check_command(self) -> None:
        result = runner.invoke(app, ["config", "check"])
        assert result.exit_code == 0

    def test_config_path_command(self) -> None:
        result = runner.invoke(app, ["config", "path"])
        assert result.exit_code == 0
        assert ".hybridcoder" in result.output

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
        from hybridcoder.config import HybridCoderConfig
        from hybridcoder.layer4.llm import OllamaProvider, create_provider

        config = HybridCoderConfig()
        provider = create_provider(config)
        assert isinstance(provider, OllamaProvider)

    def test_create_provider_openrouter(self) -> None:
        from hybridcoder.config import HybridCoderConfig
        from hybridcoder.layer4.llm import OpenRouterProvider, create_provider

        config = HybridCoderConfig()
        config.llm.provider = "openrouter"
        provider = create_provider(config)
        assert isinstance(provider, OpenRouterProvider)

    def test_conversation_history(self) -> None:
        from hybridcoder.layer4.llm import ConversationHistory

        h = ConversationHistory(system_prompt="test")
        h.add_user("hello")
        h.add_assistant("hi")
        msgs = h.get_messages()
        assert len(msgs) == 3
        assert msgs[0]["role"] == "system"
        assert msgs[1]["role"] == "user"
        assert msgs[2]["role"] == "assistant"

    def test_conversation_trim_preserves_pairs(self) -> None:
        from hybridcoder.layer4.llm import ConversationHistory

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
        from hybridcoder.layer4.llm import ConversationHistory

        h = ConversationHistory()
        h.add_user("a" * 400)
        assert h.token_estimate() == 100


class TestSprint1FileTools:
    """S1.4: File tools work with path safety."""

    def test_read_write_roundtrip(self, tmp_path: Path) -> None:
        from hybridcoder.utils.file_tools import read_file, write_file

        write_file(tmp_path / "test.txt", "hello world")
        content = read_file(str(tmp_path / "test.txt"))
        assert content == "hello world"

    def test_read_line_range(self, tmp_path: Path) -> None:
        from hybridcoder.utils.file_tools import read_file, write_file

        write_file(tmp_path / "lines.txt", "a\nb\nc\nd\n")
        content = read_file(str(tmp_path / "lines.txt"), start_line=2, end_line=3)
        assert "b" in content
        assert "c" in content
        assert "a" not in content

    def test_path_traversal_blocked(self, tmp_path: Path) -> None:
        from hybridcoder.utils.file_tools import read_file

        (tmp_path / "sub").mkdir()
        (tmp_path / "secret.txt").write_text("secret")
        with pytest.raises(ValueError, match="escapes project root"):
            read_file(str(tmp_path / "secret.txt"), project_root=str(tmp_path / "sub"))

    def test_prefix_bypass_blocked(self, tmp_path: Path) -> None:
        from hybridcoder.utils.file_tools import read_file

        repo = tmp_path / "repo"
        repo.mkdir()
        evil = tmp_path / "repo-evil"
        evil.mkdir()
        (evil / "steal.txt").write_text("stolen")
        with pytest.raises(ValueError, match="escapes project root"):
            read_file(str(evil / "steal.txt"), project_root=str(repo))

    def test_relative_path_resolves(self, tmp_path: Path) -> None:
        from hybridcoder.utils.file_tools import read_file, write_file

        (tmp_path / "src").mkdir()
        write_file("src/test.txt", "content", project_root=str(tmp_path))
        result = read_file("src/test.txt", project_root=str(tmp_path))
        assert result == "content"

    def test_list_files(self, tmp_path: Path) -> None:
        from hybridcoder.utils.file_tools import list_files

        (tmp_path / "a.py").write_text("a")
        (tmp_path / "b.txt").write_text("b")
        all_files = list_files(str(tmp_path))
        assert len(all_files) == 2
        py_files = list_files(str(tmp_path), pattern="*.py")
        assert len(py_files) == 1


class TestSprint1CoreTypes:
    """S1.5: Core types are defined correctly."""

    def test_request_type_enum(self) -> None:
        from hybridcoder.core.types import RequestType

        assert len(RequestType) == 7
        assert RequestType.CHAT.value == "chat"
        assert RequestType.DETERMINISTIC_QUERY.value == "deterministic"

    def test_layer_result_enum(self) -> None:
        from hybridcoder.core.types import LayerResult

        assert LayerResult.ESCALATE.value == "escalate"

    def test_request_dataclass(self) -> None:
        from hybridcoder.core.types import Request, RequestType

        req = Request(raw_input="test", request_type=RequestType.CHAT)
        assert req.file_context is None
        assert req.conversation_history == []

    def test_response_dataclass(self) -> None:
        from hybridcoder.core.types import Response

        resp = Response(content="hello", layer_used=4)
        assert resp.success is True
        assert resp.tokens_used == 0
        assert resp.files_modified == []

    def test_all_types_importable(self) -> None:
        from hybridcoder.core.types import (
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
        assert all([
            RequestType, LayerResult, Request, Response,
            FileRange, Symbol, CodeChunk, SearchResult, EditResult,
        ])


# ============================================================
# Sprint 2+: Add sections below as sprints are completed
# ============================================================

# class TestSprint2EditSystem:
#     """S2: Edit system verification."""
#     pass
