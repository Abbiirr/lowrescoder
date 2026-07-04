"""Tests for display_width — inspired by sharkdp/bat terminal rendering.

bat calculates display widths when aligning line numbers and syntax highlights.
A tab character advances to the *next* tab stop, not just one column. The bug
is treating '\\t' as width 1 (via len()), which makes tab-containing lines
appear shorter than they really are and misaligns the ruler.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def test_empty_string():
    from display_width import display_width
    assert display_width("") == 0


def test_no_tabs():
    from display_width import display_width
    assert display_width("hello") == 5


def test_spaces_only():
    from display_width import display_width
    # spaces are width 1 each — no difference between bug and fix
    assert display_width("   ") == 3


def test_no_tabs_mixed():
    from display_width import display_width
    assert display_width("hello world") == 11


def test_single_tab_at_start():
    from display_width import display_width
    # '\\t' at col 0 → next stop at col 4; then "hello" (5 chars) → total 9
    # Bug: len("\\thello") = 6
    result = display_width("\thello")
    assert result == 9, f"expected 9, got {result}"


def test_tab_in_middle():
    from display_width import display_width
    # "ab" (2 chars) + '\\t' → next stop at col 4 (2 spaces) + "cd" (2 chars) = 6
    # Bug: len("ab\\tcd") = 5
    result = display_width("ab\tcd")
    assert result == 6, f"expected 6, got {result}"


def test_multiple_tabs():
    from display_width import display_width
    # '\\t' at col 0 → 4; '\\t' at col 4 → 8
    # Bug: len("\\t\\t") = 2
    result = display_width("\t\t")
    assert result == 8, f"expected 8, got {result}"
