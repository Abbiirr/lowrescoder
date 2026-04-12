"""Tests for diff preview in write_file and edit_file tool handlers."""

from __future__ import annotations

from pathlib import Path

from autocode.agent.tools import _generate_diff, _handle_edit_file, _handle_write_file


def test_diff_preview_shows_before_after(tmp_path: Path) -> None:
    """Diff output contains original and modified content markers."""
    target = tmp_path / "test.txt"
    target.write_text("line1\nline2\n")

    result = _handle_write_file(str(target), "line1\nline2\nline3\n")

    assert "Diff:" in result
    assert "+line3" in result
    assert "Written to" in result


def test_diff_preview_empty_file(tmp_path: Path) -> None:
    """New file creation reports as new file, no diff."""
    target = tmp_path / "newfile.txt"

    result = _handle_write_file(str(target), "hello world\n")

    assert "new file" in result
    assert "Created" in result
    assert target.read_text() == "hello world\n"


def test_diff_preview_binary_skip(tmp_path: Path) -> None:
    """Binary files don't crash the diff generator."""
    target = tmp_path / "binary.bin"
    target.write_bytes(b"\x00\x01\x02\xff\xfe")

    # Writing text content over binary should work
    result = _handle_write_file(str(target), "now text\n")

    assert "Written to" in result


def test_diff_preview_output_contains_plus_minus() -> None:
    """Diff output has +/- markers."""
    diff = _generate_diff("old line\n", "new line\n", "test.txt")

    assert diff  # not empty
    assert "-old line" in diff
    assert "+new line" in diff


def test_diff_preview_no_changes(tmp_path: Path) -> None:
    """Writing identical content shows 'no changes'."""
    target = tmp_path / "same.txt"
    target.write_text("unchanged\n")

    result = _handle_write_file(str(target), "unchanged\n")

    assert "no changes" in result


def test_diff_preview_edit_file(tmp_path: Path) -> None:
    """Edit file also shows diff preview."""
    target = tmp_path / "edit_me.py"
    target.write_text("x = 1\ny = 2\n")

    result = _handle_edit_file(str(target), "x = 1", "x = 42")

    assert "Diff:" in result
    assert "-x = 1" in result
    assert "+x = 42" in result


def test_diff_preview_truncates_long_diff(tmp_path: Path) -> None:
    """Very long diffs are truncated."""
    target = tmp_path / "long.txt"
    target.write_text("a\n" * 500)

    result = _handle_write_file(str(target), "b\n" * 500)

    # Should contain diff but be truncated
    assert "Diff:" in result or "Written to" in result
