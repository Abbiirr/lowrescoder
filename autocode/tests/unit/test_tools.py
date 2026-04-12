"""Tests for the tool registry and built-in tools."""

from __future__ import annotations

import time
from pathlib import Path

from autocode.agent.tools import (
    CORE_TOOL_NAMES,
    ToolDefinition,
    ToolRegistry,
    _handle_edit_file,
    _handle_read_file,
    _handle_search_text,
    _handle_tool_search,
    _handle_write_file,
    _search_with_grep,
    _search_with_python,
    _search_with_ripgrep,
    create_default_registry,
    preview_file_change,
)


class TestToolRegistry:
    def test_register_and_get_tool(self) -> None:
        registry = ToolRegistry()
        tool = ToolDefinition(
            name="test_tool",
            description="A test tool",
            parameters={"type": "object", "properties": {}},
            handler=lambda: "ok",
        )
        registry.register(tool)
        assert registry.get("test_tool") is tool
        assert registry.get("nonexistent") is None

    def test_get_schemas_openai_format(self) -> None:
        registry = create_default_registry()
        schemas = registry.get_schemas_openai_format()
        assert len(schemas) == 23
        names = {s["function"]["name"] for s in schemas}
        assert names == {
            "read_file", "write_file", "edit_file", "list_files",
            "search_text", "run_command", "ask_user",
            "find_references", "find_definition", "get_type_info",
            "list_symbols", "search_code", "semantic_search", "tool_search",
            # Typed git tools (deep-research-report Lane A)
            "git_status", "git_diff", "git_log",
            # Typed web fetch (deep-research-report Lane A)
            "web_fetch",
            # Transactional multi-file patch (deep-research-report Phase B)
            "apply_patch",
            # LSP tools via Jedi (deep-research-report Phase B Item 3)
            "lsp_goto_definition", "lsp_find_references",
            "lsp_get_type", "lsp_symbols",
        }
        for schema in schemas:
            assert schema["type"] == "function"
            assert "description" in schema["function"]
            assert "parameters" in schema["function"]

    def test_read_file_tool_handler(self, tmp_path: Path) -> None:
        test_file = tmp_path / "hello.txt"
        test_file.write_text("hello world")
        result = _handle_read_file(path=str(test_file))
        assert result == "hello world"

    def test_write_file_tool_handler(self, tmp_path: Path) -> None:
        target = tmp_path / "output.txt"
        result = _handle_write_file(path=str(target), content="new content")
        assert "Created" in result or "Written to" in result
        assert target.read_text() == "new content"

    def test_write_file_blocks_external_conflict(self, tmp_path: Path) -> None:
        """write_file refuses to overwrite a file changed since last observation."""
        target = tmp_path / "output.txt"
        target.write_text("before")
        _handle_read_file(path=str(target))
        time.sleep(0.05)
        target.write_text("externally changed")

        result = _handle_write_file(path=str(target), content="new content")
        assert "Error writing file:" in result
        assert "Re-read the file" in result
        assert target.read_text() == "externally changed"

    def test_search_text_tool_handler(self, tmp_path: Path) -> None:
        (tmp_path / "code.py").write_text("def hello():\n    return 'world'\n")
        (tmp_path / "other.txt").write_text("no match here")
        result = _handle_search_text(pattern="def hello", directory=str(tmp_path))
        assert "code.py" in result
        assert "hello" in result

    def test_run_command_disabled_by_default(self) -> None:
        """run_command tool requires approval."""
        registry = create_default_registry()
        tool = registry.get("run_command")
        assert tool is not None
        assert tool.requires_approval is True

    def test_ask_user_tool_registered(self) -> None:
        """ask_user tool is registered and does not require approval."""
        registry = create_default_registry()
        tool = registry.get("ask_user")
        assert tool is not None
        assert tool.requires_approval is False
        assert "question" in tool.parameters["properties"]

    def test_ask_user_schema_has_options(self) -> None:
        """ask_user schema includes options and allow_text parameters."""
        registry = create_default_registry()
        schemas = registry.get_schemas_openai_format()
        ask_user_schema = next(
            s for s in schemas if s["function"]["name"] == "ask_user"
        )
        props = ask_user_schema["function"]["parameters"]["properties"]
        assert "question" in props
        assert "options" in props
        assert "allow_text" in props
        assert props["options"]["type"] == "array"


class TestSearchEfficiency:
    """Tests for search_text performance and correctness across backends."""

    def _create_test_tree(self, tmp_path: Path, num_files: int = 50) -> None:
        """Create a directory tree with many files for search testing."""
        for i in range(num_files):
            subdir = tmp_path / f"pkg{i % 5}"
            subdir.mkdir(exist_ok=True)
            f = subdir / f"mod{i}.py"
            f.write_text(
                f"# Module {i}\n"
                f"def function_{i}():\n"
                f"    return {i}\n"
                f"\n"
                f"class Widget{i}:\n"
                f"    pass\n"
            )
        # Add a unique target
        target = tmp_path / "pkg0" / "target.py"
        target.write_text("def unique_needle():\n    return 42\n")

    def test_python_fallback_finds_matches(self, tmp_path: Path) -> None:
        """Pure Python search finds the correct results."""
        self._create_test_tree(tmp_path)
        result = _search_with_python("unique_needle", str(tmp_path), "**/*", 50)
        assert "target.py" in result
        assert "unique_needle" in result

    def test_python_fallback_respects_max_results(self, tmp_path: Path) -> None:
        """Python search stops at max_results."""
        self._create_test_tree(tmp_path)
        result = _search_with_python("def ", str(tmp_path), "**/*", 5)
        lines = result.strip().splitlines()
        # 5 results + 1 truncation message
        assert len(lines) <= 6

    def test_python_search_with_glob_filter(self, tmp_path: Path) -> None:
        """Python search respects glob_pattern filter."""
        self._create_test_tree(tmp_path)
        (tmp_path / "data.txt").write_text("unique_needle in txt\n")
        result = _search_with_python("unique_needle", str(tmp_path), "**/*.py", 50)
        assert "target.py" in result
        assert "data.txt" not in result

    def test_grep_returns_none_if_unavailable(self, tmp_path: Path) -> None:
        """grep search returns None if grep binary isn't found."""
        import unittest.mock
        with unittest.mock.patch("shutil.which", return_value=None):
            result = _search_with_grep("test", str(tmp_path), "**/*", 50)
        assert result is None

    def test_ripgrep_returns_none_if_unavailable(self, tmp_path: Path) -> None:
        """ripgrep search returns None if rg binary isn't found."""
        import unittest.mock
        with unittest.mock.patch("shutil.which", return_value=None):
            result = _search_with_ripgrep("test", str(tmp_path), "**/*", 50)
        assert result is None

    def test_search_text_uses_fallback_chain(self, tmp_path: Path) -> None:
        """_handle_search_text always returns a result regardless of backend."""
        self._create_test_tree(tmp_path)
        result = _handle_search_text("unique_needle", str(tmp_path))
        assert "unique_needle" in result

    def test_python_search_performance(self, tmp_path: Path) -> None:
        """Python search completes within a reasonable time for 50 files."""
        self._create_test_tree(tmp_path, num_files=50)
        start = time.monotonic()
        _search_with_python("function_", str(tmp_path), "**/*.py", 50)
        duration = time.monotonic() - start
        # Should complete in under 2 seconds even on slow disk
        assert duration < 2.0

    def test_search_invalid_regex(self, tmp_path: Path) -> None:
        """Invalid regex patterns return an error message."""
        result = _handle_search_text("[invalid", str(tmp_path))
        assert "Invalid regex" in result

    def test_search_nonexistent_directory(self) -> None:
        """Searching a nonexistent directory returns an error."""
        result = _handle_search_text("test", "/nonexistent/path/xyz")
        # All backends will fail; Python fallback returns error
        assert "No matches" in result or "Not a directory" in result


class TestEditFileTool:
    """Tests for the edit_file tool."""

    def test_basic_replacement(self, tmp_path: Path) -> None:
        """edit_file replaces a unique string occurrence."""
        f = tmp_path / "code.py"
        f.write_text("def hello():\n    return 'world'\n")
        result = _handle_edit_file(
            path=str(f), old_string="return 'world'", new_string="return 'earth'",
        )
        assert "Edited" in result
        assert f.read_text() == "def hello():\n    return 'earth'\n"

    def test_no_match_error(self, tmp_path: Path) -> None:
        """edit_file returns error when old_string is not found."""
        f = tmp_path / "code.py"
        f.write_text("def hello():\n    pass\n")
        result = _handle_edit_file(
            path=str(f), old_string="nonexistent", new_string="replacement",
        )
        assert "Error" in result
        assert "not found" in result

    def test_ambiguous_match_error(self, tmp_path: Path) -> None:
        """edit_file returns error when old_string matches multiple times."""
        f = tmp_path / "code.py"
        f.write_text("x = 1\nx = 2\n")
        result = _handle_edit_file(
            path=str(f), old_string="x = ", new_string="y = ",
        )
        assert "Error" in result
        assert "2 times" in result

    def test_empty_old_string_error(self, tmp_path: Path) -> None:
        """edit_file returns error when old_string is empty."""
        f = tmp_path / "code.py"
        f.write_text("content\n")
        result = _handle_edit_file(
            path=str(f), old_string="", new_string="new",
        )
        assert "Error" in result
        assert "empty" in result

    def test_preserves_surrounding_content(self, tmp_path: Path) -> None:
        """edit_file preserves content before and after the replacement."""
        f = tmp_path / "code.py"
        original = "line1\nline2\nline3\nline4\n"
        f.write_text(original)
        result = _handle_edit_file(
            path=str(f), old_string="line2\nline3", new_string="replaced2\nreplaced3",
        )
        assert "Edited" in result
        assert f.read_text() == "line1\nreplaced2\nreplaced3\nline4\n"

    def test_registered_in_registry(self) -> None:
        """edit_file is registered in the default registry."""
        registry = create_default_registry()
        tool = registry.get("edit_file")
        assert tool is not None
        assert tool.requires_approval is True
        assert tool.mutates_fs is True
        assert "old_string" in tool.parameters["properties"]
        assert "new_string" in tool.parameters["properties"]

    def test_edit_file_warns_after_external_change(self, tmp_path: Path) -> None:
        """edit_file applies the targeted edit but warns after an external change."""
        f = tmp_path / "code.py"
        f.write_text("keep\nreplace me\n")
        _handle_read_file(path=str(f))
        time.sleep(0.05)
        f.write_text("changed elsewhere\nreplace me\n")

        result = _handle_edit_file(
            path=str(f),
            old_string="replace me",
            new_string="done",
        )
        assert "Warning: file changed since the last observation" in result
        assert "done" in f.read_text()

    def test_preview_file_change_builds_diff(self, tmp_path: Path) -> None:
        """Approval previews build the proposed before/after view."""
        f = tmp_path / "code.py"
        f.write_text("x = 1\n")

        preview = preview_file_change(
            "edit_file",
            {
                "path": str(f),
                "old_string": "x = 1",
                "new_string": "x = 2",
            },
        )

        assert preview.before == "x = 1\n"
        assert preview.after == "x = 2\n"


class TestDeferredToolLoading:
    """Tests for deferred tool loading (tool_search, core schemas, deferred names)."""

    def test_core_tool_names_contains_expected(self) -> None:
        """CORE_TOOL_NAMES includes the essential tools."""
        expected = {
            "read_file",
            "write_file",
            "edit_file",
            "list_files",
            "run_command",
            "search_text",
            "tool_search",
            # Typed git tools (deep-research-report Lane A)
            "git_status",
            "git_diff",
            "git_log",
            # Typed web fetch (deep-research-report Lane A)
            "web_fetch",
            # Transactional multi-file patch (deep-research-report Phase B)
            "apply_patch",
        }
        assert expected == CORE_TOOL_NAMES

    def test_tool_search_handler_returns_matching_tools(self) -> None:
        """tool_search returns tools matching the query."""
        registry = create_default_registry()
        result = _handle_tool_search(query="symbol", tool_registry=registry)
        # Should match find_references, find_definition, get_type_info, list_symbols
        assert "find_references" in result
        assert "find_definition" in result
        assert "list_symbols" in result
        assert "These tools are now available for use." in result

    def test_tool_search_handler_no_matches(self) -> None:
        """tool_search returns a useful message when nothing matches."""
        registry = create_default_registry()
        result = _handle_tool_search(query="zzz_nonexistent_zzz", tool_registry=registry)
        assert "No tools found" in result

    def test_tool_search_case_insensitive(self) -> None:
        """tool_search matches case-insensitively."""
        registry = create_default_registry()
        result = _handle_tool_search(query="SEARCH", tool_registry=registry)
        assert "search_text" in result

    def test_get_core_schemas_openai_format_returns_only_core(self) -> None:
        """get_core_schemas_openai_format returns only the core tools."""
        registry = create_default_registry()
        core_schemas = registry.get_core_schemas_openai_format()
        core_names = {s["function"]["name"] for s in core_schemas}
        # tool_search is core but we need to check it's registered first
        # After create_default_registry it won't have tool_search unless we add it
        # So check that core_names is a subset of CORE_TOOL_NAMES
        assert core_names <= CORE_TOOL_NAMES
        # And non-core tools are excluded
        assert "find_references" not in core_names
        assert "search_code" not in core_names

    def test_get_deferred_tool_names_returns_non_core(self) -> None:
        """get_deferred_tool_names returns tools not in CORE_TOOL_NAMES."""
        registry = create_default_registry()
        deferred = registry.get_deferred_tool_names()
        # Deferred tools should include L1/L2 tools
        assert "find_references" in deferred
        assert "search_code" in deferred
        assert "semantic_search" in deferred
        assert "list_symbols" in deferred
        # Core tools should NOT be in deferred
        assert "read_file" not in deferred
        assert "write_file" not in deferred
        assert "list_files" not in deferred
        assert "run_command" not in deferred

    def test_tool_search_shows_parameter_schemas(self) -> None:
        """tool_search result includes parameter information."""
        registry = create_default_registry()
        result = _handle_tool_search(query="read_file", tool_registry=registry)
        assert "read_file" in result
        assert "path" in result
