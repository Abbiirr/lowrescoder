"""Tests for HybridCompleter and HybridAutoSuggest."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from prompt_toolkit.document import Document

from hybridcoder.inline.completer import HybridAutoSuggest, HybridCompleter
from hybridcoder.tui.commands import create_default_router


def _make_completer(tmp_path: Path) -> HybridCompleter:
    """Create a completer with default router."""
    router = create_default_router()
    return HybridCompleter(router, tmp_path)


def _make_auto_suggest() -> HybridAutoSuggest:
    """Create an auto-suggest with default router."""
    return HybridAutoSuggest(create_default_router())


class TestHybridCompleter:
    def test_slash_command_completion(self, tmp_path: Path) -> None:
        """/he yields 'help' completion."""
        completer = _make_completer(tmp_path)
        doc = Document("/he", cursor_position=3)
        completions = list(completer.get_completions(doc, None))
        names = [c.text for c in completions]
        assert "help" in names

    def test_slash_command_all(self, tmp_path: Path) -> None:
        """/ yields all command completions."""
        completer = _make_completer(tmp_path)
        doc = Document("/", cursor_position=1)
        completions = list(completer.get_completions(doc, None))
        # Should include all 12 commands + aliases
        names = [c.text for c in completions]
        assert "exit" in names
        assert "help" in names
        assert "model" in names
        assert len(names) >= 12

    def test_at_file_completion(self, tmp_path: Path) -> None:
        """@README yields README.md when file exists."""
        (tmp_path / "README.md").write_text("# Test")
        completer = _make_completer(tmp_path)
        doc = Document("@README", cursor_position=7)
        completions = list(completer.get_completions(doc, None))
        names = [c.text for c in completions]
        assert "README.md" in names

    def test_no_completion_for_regular_text(self, tmp_path: Path) -> None:
        """Regular text yields no completions."""
        completer = _make_completer(tmp_path)
        doc = Document("hello world", cursor_position=11)
        completions = list(completer.get_completions(doc, None))
        assert len(completions) == 0

    def test_mixed_text_with_at(self, tmp_path: Path) -> None:
        """'read @RE' yields README.md completion."""
        (tmp_path / "README.md").write_text("# Test")
        completer = _make_completer(tmp_path)
        doc = Document("read @RE", cursor_position=8)
        completions = list(completer.get_completions(doc, None))
        names = [c.text for c in completions]
        assert "README.md" in names


class TestHybridAutoSuggest:
    def test_slash_command_ghost_text(self) -> None:
        """/res suggests 'ume' as ghost text."""
        suggest = _make_auto_suggest()
        doc = Document("/res", cursor_position=4)
        buf = MagicMock()
        result = suggest.get_suggestion(buf, doc)
        assert result is not None
        assert result.text == "ume"

    def test_slash_command_full_match_no_ghost(self) -> None:
        """/resume (exact match) produces no ghost text."""
        suggest = _make_auto_suggest()
        doc = Document("/resume", cursor_position=7)
        buf = MagicMock()
        result = suggest.get_suggestion(buf, doc)
        assert result is None

    def test_slash_alias_ghost_text(self) -> None:
        """/q suggests ghost text for 'quit' alias."""
        suggest = _make_auto_suggest()
        doc = Document("/qu", cursor_position=3)
        buf = MagicMock()
        result = suggest.get_suggestion(buf, doc)
        assert result is not None
        assert result.text == "it"

    def test_no_ghost_for_regular_text(self) -> None:
        """Regular text produces no ghost text."""
        suggest = _make_auto_suggest()
        doc = Document("hello", cursor_position=5)
        buf = MagicMock()
        result = suggest.get_suggestion(buf, doc)
        assert result is None

    def test_bare_slash_no_ghost(self) -> None:
        """Bare / produces no ghost text (too many options)."""
        suggest = _make_auto_suggest()
        doc = Document("/", cursor_position=1)
        buf = MagicMock()
        result = suggest.get_suggestion(buf, doc)
        assert result is None
