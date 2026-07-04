import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from text_stats import count_words

# PASS (single spaces — bug and fix agree)

def test_two_words():
    assert count_words('hello world') == 2

def test_three_words():
    assert count_words('one two three') == 3

def test_single_word():
    assert count_words('word') == 1

def test_four_words():
    assert count_words('foo bar baz qux') == 4

# FAIL (edge cases where split(' ') disagrees with split())

def test_empty_string():
    assert count_words('') == 0  # bug: split(' ') = [''] → 1

def test_double_space():
    assert count_words('hello  world') == 2  # bug: split(' ') → 3 (empty token)

def test_tab_separator():
    assert count_words('hello\tworld') == 2  # bug: split(' ') → 1 (tab not split)
