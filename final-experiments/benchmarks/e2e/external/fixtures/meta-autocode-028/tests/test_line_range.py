import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
import pytest
from line_range import filter_lines

LINES = ["line1", "line2", "line3", "line4", "line5", "line6", "line7", "line8", "line9", "line10"]

def test_multi_line_range_from_start():
    assert filter_lines(LINES, 1, 3) == ["line1", "line2", "line3"]

def test_multi_line_range_in_middle():
    assert filter_lines(LINES, 4, 6) == ["line4", "line5", "line6"]

def test_multi_line_range_to_end():
    assert filter_lines(LINES, 8, 10) == ["line8", "line9", "line10"]

def test_two_line_range():
    assert filter_lines(LINES, 3, 4) == ["line3", "line4"]

def test_single_line_at_start():
    # BUG: start==end triggers the >= guard, returns [] instead of ["line1"]
    assert filter_lines(LINES, 1, 1) == ["line1"]

def test_single_line_in_middle():
    # BUG: 5:5 returns [] instead of ["line5"]
    assert filter_lines(LINES, 5, 5) == ["line5"]

def test_single_line_at_end():
    # BUG: 10:10 returns [] instead of ["line10"]
    assert filter_lines(LINES, 10, 10) == ["line10"]
