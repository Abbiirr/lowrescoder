import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from line_analyzer import max_line_length

# PASS (empty, or last line is NOT the longest — bug and fix agree)

def test_empty():
    assert max_line_length([]) == 0

def test_last_not_longest():
    assert max_line_length(['hello', 'hi', 'x']) == 5

def test_last_shorter():
    assert max_line_length(['ab', 'cde', 'f']) == 3

def test_max_in_middle():
    assert max_line_length(['long line here', 'short', 'mid']) == 14

# FAIL (last line IS the longest — bug skips it and returns wrong value)

def test_last_is_longest():
    assert max_line_length(['a', 'b', 'longer']) == 6  # bug: 1

def test_two_lines_last_longer():
    assert max_line_length(['hi', 'hello world']) == 11  # bug: 2

def test_single_long_last():
    assert max_line_length(['x', 'looooooong']) == 10  # bug: 1
