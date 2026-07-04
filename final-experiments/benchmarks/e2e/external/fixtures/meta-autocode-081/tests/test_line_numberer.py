import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from line_numberer import number_lines

# PASS with bug

def test_empty_returns_empty():
    assert number_lines([]) == []

def test_single_line_is_list():
    result = number_lines(['hello'])
    assert isinstance(result, list) and len(result) == 1

def test_preserves_line_content():
    result = number_lines(['abc', 'def'])
    assert result[0][1] == 'abc'
    assert result[1][1] == 'def'

def test_length_matches_input():
    lines = ['a', 'b', 'c', 'd', 'e']
    assert len(number_lines(lines)) == 5

# FAIL with bug (start ignored, always 0-based)

def test_default_start_is_1():
    result = number_lines(['x'])
    assert result[0][0] == 1  # bug returns 0

def test_start_param_respected():
    result = number_lines(['x', 'y'], start=5)
    assert result[0][0] == 5  # bug returns 0

def test_large_start_offset():
    result = number_lines(['a', 'b', 'c'], start=100)
    assert result[2][0] == 102  # bug returns 2
