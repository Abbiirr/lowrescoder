import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from line_counter import count_lines

# PASS (text ends with non-newline — bug and fix agree)

def test_single_line():
    assert count_lines('hello') == 1

def test_two_lines():
    assert count_lines('hello\nworld') == 2

def test_three_lines():
    assert count_lines('a\nb\nc') == 3

def test_four_lines():
    assert count_lines('line1\nline2\nline3\nline4') == 4

# FAIL (empty string or trailing newline — bug inflates count by 1)

def test_empty_string():
    assert count_lines('') == 0  # bug: 1

def test_trailing_newline():
    assert count_lines('hello\n') == 1  # bug: 2

def test_two_lines_trailing_newline():
    assert count_lines('a\nb\n') == 2  # bug: 3
