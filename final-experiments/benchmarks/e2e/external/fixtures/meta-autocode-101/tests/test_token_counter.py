import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from token_counter import count_tokens

# PASS with bug (single char or empty)

def test_empty_string():
    assert count_tokens('') == 0

def test_single_char_is_one():
    assert count_tokens('a') == 1  # bug: 1 char → 1; word count also 1

def test_returns_int():
    assert isinstance(count_tokens('hello'), int)

def test_short_word_positive():
    assert count_tokens('hi') > 0  # both agree > 0

# FAIL with bug (multi-word input: char count >> word count)

def test_two_word_count():
    assert count_tokens('hello world') == 2  # bug: 11 (chars)

def test_three_word_count():
    assert count_tokens('the quick fox') == 3  # bug: 13

def test_sentence_token_count():
    assert count_tokens('I love open source') == 4  # bug: 18
