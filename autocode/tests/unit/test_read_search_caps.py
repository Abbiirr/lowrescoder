"""Tests for mandatory caps on read_file and search_text.

Phase A Item 2 of the deep-research-report gap analysis: unbounded reads
and unbounded searches are the primary source of token blowups. These
caps are enforced at the tool-handler layer so the agent cannot
accidentally blow up its own context by reading a 50k-line minified JS
file or pattern-matching against a huge codebase with no filter.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from autocode.agent.tools import (
    _READ_FILE_DEFAULT_MAX_LINES,
    _READ_FILE_MAX_BYTES,
    _SEARCH_TEXT_MAX_BYTES,
    _SEARCH_TEXT_MAX_RESULTS_CAP,
    _handle_read_file,
    _handle_search_text,
)


# --- read_file caps ---


class TestReadFileLineCap:
    def test_short_file_not_truncated(self, tmp_path: Path) -> None:
        """Files under the line cap return without any truncation marker."""
        f = tmp_path / "short.txt"
        f.write_text("\n".join(f"line {i}" for i in range(50)))
        result = _handle_read_file(path=str(f))
        assert "line 49" in result
        assert "truncated" not in result.lower()

    def test_unbounded_read_caps_long_file(self, tmp_path: Path) -> None:
        """A file with > DEFAULT_MAX_LINES lines gets auto-truncated."""
        n = _READ_FILE_DEFAULT_MAX_LINES + 500
        f = tmp_path / "long.txt"
        f.write_text("\n".join(f"line {i}" for i in range(n)))
        result = _handle_read_file(path=str(f))
        assert "truncated" in result.lower()
        assert f"{_READ_FILE_DEFAULT_MAX_LINES} lines" in result
        # First line must still be present
        assert "line 0" in result
        # Last pre-cap line should be present
        assert f"line {_READ_FILE_DEFAULT_MAX_LINES - 1}" in result
        # Line well past the cap should NOT be present
        assert f"line {_READ_FILE_DEFAULT_MAX_LINES + 400}" not in result

    def test_explicit_end_line_bypasses_auto_cap(self, tmp_path: Path) -> None:
        """When the caller passes end_line explicitly, no auto line truncation."""
        n = _READ_FILE_DEFAULT_MAX_LINES + 100
        f = tmp_path / "long.txt"
        f.write_text("\n".join(f"line {i}" for i in range(n)))
        # Read a specific range that extends past the default cap
        result = _handle_read_file(
            path=str(f), start_line=1, end_line=_READ_FILE_DEFAULT_MAX_LINES + 50
        )
        # The "auto-truncated at N lines" marker should NOT appear
        assert f"truncated at {_READ_FILE_DEFAULT_MAX_LINES} lines" not in result

    def test_start_line_without_end_line_still_auto_caps(self, tmp_path: Path) -> None:
        """Unbounded tail read (start_line set, end_line None) still gets capped."""
        n = _READ_FILE_DEFAULT_MAX_LINES + 500
        f = tmp_path / "long.txt"
        f.write_text("\n".join(f"line {i}" for i in range(n)))
        result = _handle_read_file(path=str(f), start_line=1)
        assert "truncated" in result.lower()


class TestReadFileByteCap:
    def test_single_giant_line_gets_byte_capped(self, tmp_path: Path) -> None:
        """A single line larger than the byte cap is still truncated."""
        big = "x" * (_READ_FILE_MAX_BYTES + 1000)
        f = tmp_path / "giant-line.txt"
        f.write_text(big)
        result = _handle_read_file(path=str(f))
        # Result must be smaller than the full content
        assert len(result.encode("utf-8")) < len(big) + 500
        assert "truncated" in result.lower()

    def test_normal_file_not_byte_capped(self, tmp_path: Path) -> None:
        """Files well under the byte cap are returned intact."""
        content = "\n".join(f"line {i}" for i in range(20))
        f = tmp_path / "normal.txt"
        f.write_text(content)
        result = _handle_read_file(path=str(f))
        assert "line 0" in result
        assert "line 19" in result
        assert "truncated" not in result.lower()


class TestReadFileErrors:
    def test_nonexistent_file_returns_error(self, tmp_path: Path) -> None:
        result = _handle_read_file(path=str(tmp_path / "missing.txt"))
        assert "Error reading file" in result


# --- search_text caps ---


class TestSearchTextMaxResultsCap:
    def test_default_max_results_is_50(self, tmp_path: Path) -> None:
        """Without max_results, search returns at most ~50 hits."""
        # Create a file with many matches
        f = tmp_path / "many.txt"
        f.write_text("\n".join(f"match {i} FOO" for i in range(200)))
        result = _handle_search_text(pattern="FOO", directory=str(tmp_path))
        # Be lenient on exact backend behavior — just make sure we don't get
        # more than ~60 matches back (50 + header/footer lines)
        hit_count = result.count("FOO")
        assert hit_count <= 60, f"expected <= 60 hits with default cap, got {hit_count}"

    def test_max_results_clamped_to_hard_cap(self, tmp_path: Path) -> None:
        """Requesting max_results=10000 is silently clamped to the hard cap."""
        f = tmp_path / "many.txt"
        f.write_text("\n".join(f"match {i} FOO" for i in range(800)))
        result = _handle_search_text(
            pattern="FOO", directory=str(tmp_path), max_results=10_000
        )
        # Hard cap is _SEARCH_TEXT_MAX_RESULTS_CAP; we should see at most
        # that many occurrences of FOO (plus a bit of noise for formatting)
        hit_count = result.count("FOO")
        assert hit_count <= _SEARCH_TEXT_MAX_RESULTS_CAP + 20

    def test_max_results_negative_defaults(self, tmp_path: Path) -> None:
        """Negative or zero max_results is clamped back to the default (50)."""
        f = tmp_path / "many.txt"
        f.write_text("\n".join(f"match {i} FOO" for i in range(200)))
        # No crash, no exception
        result = _handle_search_text(
            pattern="FOO", directory=str(tmp_path), max_results=-5
        )
        assert "FOO" in result


class TestSearchTextByteCap:
    def test_giant_results_get_byte_truncated(self, tmp_path: Path) -> None:
        """If a single huge matching line would blow the byte cap, truncate."""
        # One match, but the line itself is very long
        huge_line = "FOO " + ("x" * (_SEARCH_TEXT_MAX_BYTES + 5000))
        f = tmp_path / "huge.txt"
        f.write_text(huge_line)
        result = _handle_search_text(pattern="FOO", directory=str(tmp_path))
        # Result should be capped around SEARCH_TEXT_MAX_BYTES plus a short
        # truncation marker tail
        assert len(result) < _SEARCH_TEXT_MAX_BYTES + 500


class TestSearchTextPassthrough:
    def test_no_matches_returns_clean_message(self, tmp_path: Path) -> None:
        f = tmp_path / "empty.txt"
        f.write_text("no interesting content here\n")
        result = _handle_search_text(pattern="DEFINITELY_NOT_PRESENT", directory=str(tmp_path))
        assert "No matches" in result or result.strip() == ""

    def test_one_match_returned(self, tmp_path: Path) -> None:
        f = tmp_path / "one.txt"
        f.write_text("prefix\nTARGET_LINE\nsuffix\n")
        result = _handle_search_text(pattern="TARGET_LINE", directory=str(tmp_path))
        assert "TARGET_LINE" in result
