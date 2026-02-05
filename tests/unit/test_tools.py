"""Tests for the tool registry and built-in tools."""

from __future__ import annotations

import time
from pathlib import Path

from hybridcoder.agent.tools import (
    ToolDefinition,
    ToolRegistry,
    _handle_read_file,
    _handle_search_text,
    _handle_write_file,
    _search_with_grep,
    _search_with_python,
    _search_with_ripgrep,
    create_default_registry,
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
        assert len(schemas) == 6
        names = {s["function"]["name"] for s in schemas}
        assert names == {
            "read_file", "write_file", "list_files",
            "search_text", "run_command", "ask_user",
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
        assert "Written to" in result
        assert target.read_text() == "new content"

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
