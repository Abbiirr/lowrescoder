import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from word_count import count_words

def test_empty_string():
    assert count_words("") == 0

def test_single_word():
    assert count_words("hello") == 1

def test_two_words():
    assert count_words("hello world") == 2

def test_three_words():
    assert count_words("one two three") == 3

def test_tab_separated_words():
    # BUG: "hello\tworld".split(' ') = ["hello\tworld"] → count=1, should be 2
    assert count_words("hello\tworld") == 2

def test_double_space_between_words():
    # BUG: "a  b".split(' ') = ["a", "", "b"] → count=3, should be 2
    assert count_words("a  b") == 2

def test_mixed_whitespace():
    # BUG: "x\t y  z".split(' ') = ["x\t", "y", "", "z"] → count=4, should be 3
    assert count_words("x\t y  z") == 3
