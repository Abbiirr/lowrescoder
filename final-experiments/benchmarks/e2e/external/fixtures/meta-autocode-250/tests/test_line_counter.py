import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from line_counter import count_lines

# PASS with bug (empty string or trailing newline — count('\n') matches splitlines())
def test_empty():
    assert count_lines('') == 0

def test_one_line_newline():
    assert count_lines('a\n') == 1

def test_two_lines_trailing():
    assert count_lines('a\nb\n') == 2

def test_three_lines_trailing():
    assert count_lines('a\nb\nc\n') == 3

# FAIL with bug (no trailing newline — count('\n') undercounts by 1)
def test_single_word_no_newline():
    assert count_lines('hello') == 1

def test_two_lines_no_trailing():
    assert count_lines('a\nb') == 2

def test_three_lines_no_trailing():
    assert count_lines('a\nb\nc') == 3
