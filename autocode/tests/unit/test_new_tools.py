"""Tests for the 5 new Layer 1/2 tools (Sprint 3G)."""

from __future__ import annotations

import textwrap

import pytest

from autocode.agent.tools import (
    create_default_registry,
)


class TestToolRegistration:
    """Verify all L1/L2 and core tools are registered."""

    def test_total_tool_count(self):
        registry = create_default_registry()
        # 14 base + 3 typed git + 1 web_fetch + 1 apply_patch + 4 LSP = 23
        assert len(registry.get_all()) == 27

    def test_new_tools_exist(self):
        registry = create_default_registry()
        expected_new = {
            "find_references", "find_definition",
            "get_type_info", "list_symbols", "search_code", "semantic_search",
        }
        registered = {t.name for t in registry.get_all()}
        assert expected_new.issubset(registered)

    def test_original_tools_preserved(self):
        registry = create_default_registry()
        original = {
            "read_file", "write_file", "list_files",
            "search_text", "run_command", "ask_user",
        }
        registered = {t.name for t in registry.get_all()}
        assert original.issubset(registered)

    def test_openai_schema_count(self):
        registry = create_default_registry()
        schemas = registry.get_schemas_openai_format()
        # 14 base + 3 typed git + 1 web_fetch + 1 apply_patch + 4 LSP = 23
        assert len(schemas) == 27

    def test_new_tools_no_approval(self):
        """L1/L2 tools should not require approval."""
        registry = create_default_registry()
        new_tools = ["find_references", "find_definition",
                     "get_type_info", "list_symbols", "search_code", "semantic_search"]
        for name in new_tools:
            tool = registry.get(name)
            assert tool is not None
            assert not tool.requires_approval


class TestNewToolHandlers:
    """Test the new tool handlers with real tree-sitter parsing."""

    @pytest.fixture
    def sample_project(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "module.py").write_text(textwrap.dedent("""\
            import os
            from pathlib import Path

            class Parser:
                def parse(self, source: str) -> str:
                    return source.strip()

                def validate(self, code: str) -> bool:
                    return True

            def helper(x: int) -> int:
                return x + 1
        """))
        return tmp_path

    def test_find_references_handler(self, sample_project):
        from autocode.agent.tools import _handle_find_references

        result = _handle_find_references(
            symbol="Parser", project_root=str(sample_project),
        )
        assert "Parser" in result

    def test_find_definition_handler(self, sample_project):
        from autocode.agent.tools import _handle_find_definition

        result = _handle_find_definition(
            symbol="helper", project_root=str(sample_project),
        )
        assert "helper" in result

    def test_get_type_info_handler(self, sample_project):
        from autocode.agent.tools import _handle_get_type_info

        result = _handle_get_type_info(
            symbol="helper",
            file="src/module.py",
            project_root=str(sample_project),
        )
        assert "helper" in result

    def test_list_symbols_handler(self, sample_project):
        from autocode.agent.tools import _handle_list_symbols

        result = _handle_list_symbols(
            file="src/module.py", project_root=str(sample_project),
        )
        assert "Parser" in result or "helper" in result

    def test_search_code_handler(self, sample_project):
        from autocode.agent.tools import _handle_search_code

        result = _handle_search_code(
            query="parse source", project_root=str(sample_project),
        )
        # Should return results or "No results found"
        assert isinstance(result, str)

    def test_semantic_search_alias_registered(self, sample_project):
        registry = create_default_registry(project_root=str(sample_project))
        search_code = registry.get("search_code")
        semantic_search = registry.get("semantic_search")

        assert search_code is not None
        assert semantic_search is not None
        result = semantic_search.handler(query="parse source")
        assert isinstance(result, str)

    def test_find_definition_not_found(self, sample_project):
        from autocode.agent.tools import _handle_find_definition

        result = _handle_find_definition(
            symbol="nonexistent_xyz", project_root=str(sample_project),
        )
        assert "not found" in result.lower() or "nonexistent" in result
