"""Tests for display — inspired by jesseduffield/lazygit terminal rendering.

lazygit truncates branch names, commit messages, and file paths to fixed
column widths. Appending the suffix AFTER cutting to max_len is a classic
off-by-len(suffix) bug — the result overflows the column.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def test_short_text_unchanged():
    from display import truncate
    assert truncate("hi", 10) == "hi"


def test_exact_length_unchanged():
    from display import truncate
    assert truncate("hello", 5) == "hello"


def test_truncated_respects_max_len():
    from display import truncate
    result = truncate("hello world", 8)
    assert len(result) <= 8, f"expected len ≤ 8, got {len(result)}: {result!r}"


def test_truncated_ends_with_suffix():
    from display import truncate
    result = truncate("hello world", 8)
    assert result.endswith("…"), f"expected '…' suffix, got {result!r}"


def test_truncated_multi_char_suffix():
    from display import truncate
    result = truncate("hello world", 8, suffix="...")
    assert len(result) <= 8, f"expected len ≤ 8, got {len(result)}: {result!r}"
    assert result.endswith("...")


def test_pad_or_truncate_exact_width():
    from display import pad_or_truncate
    assert len(pad_or_truncate("branch-name-that-is-long", 12)) == 12


def test_pad_or_truncate_short_padded():
    from display import pad_or_truncate
    result = pad_or_truncate("main", 10)
    assert result == "main      "
    assert len(result) == 10
