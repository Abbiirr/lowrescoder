"""Tests for @file reference detection, resolution, and completion."""

from __future__ import annotations

from pathlib import Path

from autocode.tui.file_completer import (
    detect_at_references,
    expand_references,
    fuzzy_complete,
    resolve_reference,
)


class TestFileCompleter:
    def test_detect_at_references(self) -> None:
        """Detects @path references in text."""
        text = "Look at @src/main.py and @tests/test_foo.py for details"
        refs = detect_at_references(text)
        assert "src/main.py" in refs
        assert "tests/test_foo.py" in refs

    def test_detect_at_references_with_line_range(self) -> None:
        """Detects @path:line-line references."""
        text = "See @config.py:10-20 for the settings"
        refs = detect_at_references(text)
        assert "config.py:10-20" in refs

    def test_resolve_reference_full_file(self, tmp_path: Path) -> None:
        """Resolves a full file reference."""
        test_file = tmp_path / "hello.txt"
        test_file.write_text("line 1\nline 2\nline 3\n")

        content = resolve_reference("hello.txt", tmp_path)
        assert "line 1" in content
        assert "line 3" in content

    def test_resolve_reference_line_range(self, tmp_path: Path) -> None:
        """Resolves a file reference with line range."""
        test_file = tmp_path / "code.py"
        test_file.write_text("a\nb\nc\nd\ne\n")

        content = resolve_reference("code.py:2-4", tmp_path)
        assert "b" in content
        assert "d" in content
        assert "a" not in content
        assert "e" not in content

    def test_resolve_reference_missing_file(self, tmp_path: Path) -> None:
        """Returns error for missing files."""
        content = resolve_reference("missing.txt", tmp_path)
        assert "not found" in content.lower()

    def test_fuzzy_complete(self, tmp_path: Path) -> None:
        """Fuzzy completion matches partial paths."""
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("main")
        (tmp_path / "src" / "utils.py").write_text("utils")
        (tmp_path / "README.md").write_text("readme")

        results = fuzzy_complete("main", tmp_path)
        assert any("main.py" in r for r in results)

        results2 = fuzzy_complete("README", tmp_path)
        assert any("README" in r for r in results2)

    def test_expand_references(self, tmp_path: Path) -> None:
        """Expands @references in text with file contents."""
        test_file = tmp_path / "data.txt"
        test_file.write_text("important data")

        text = "Check @data.txt for info"
        expanded = expand_references(text, tmp_path)
        assert "important data" in expanded
        assert "@data.txt" not in expanded
