import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from syntax_highlighter import get_highlight_lines

# PASS with bug (range_end is exclusive in both view and highlight — consistent)

def test_empty_ranges():
    assert get_highlight_lines(1, 10, []) == set()

def test_range_fully_within_view():
    # highlight lines 3-4 (exclusive end: range (3,5)), view lines 1-9
    result = get_highlight_lines(1, 10, [(3, 5)])
    assert result == {3, 4}

def test_range_starts_at_view_start():
    result = get_highlight_lines(1, 10, [(1, 3)])
    assert result == {1, 2}

def test_multiple_ranges():
    result = get_highlight_lines(1, 20, [(2, 4), (8, 10)])
    assert result == {2, 3, 8, 9}

# FAIL with bug (range_end should be inclusive: line <= range_end)

def test_range_end_inclusive():
    # Highlight range (3, 5) should include line 5
    result = get_highlight_lines(1, 10, [(3, 5)])
    assert 5 in result  # bug: 5 < 5 is False, so 5 excluded

def test_single_line_range():
    # Highlight range (4, 4) means exactly line 4
    result = get_highlight_lines(1, 10, [(4, 4)])
    assert result == {4}  # bug: 4 < 4 is False, empty set

def test_view_end_line_highlighted():
    # View 1-10, highlight (9, 10) — line 10 should be included
    result = get_highlight_lines(1, 11, [(9, 10)])
    assert 10 in result  # bug: 10 < 10 is False
