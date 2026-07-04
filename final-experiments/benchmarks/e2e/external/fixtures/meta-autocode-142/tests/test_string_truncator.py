import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from string_truncator import truncate

# PASS with bug (short strings not truncated; ellipsis content correct)

def test_short_string_unchanged():
    assert truncate('hello', 10) == 'hello'

def test_exact_length_unchanged():
    assert truncate('hello', 5) == 'hello'

def test_ends_with_ellipsis():
    result = truncate('hello world', 7)
    assert result.endswith('...')

def test_empty_string():
    assert truncate('', 5) == ''

# FAIL with bug (result must not exceed max_length)

def test_result_length_not_exceeded():
    result = truncate('hello world', 8)
    assert len(result) <= 8  # bug: len = 8+3 = 11

def test_exact_max_length():
    result = truncate('abcdefghij', 5)
    assert len(result) == 5  # bug: 5+3 = 8

def test_truncation_fits():
    result = truncate('x' * 20, 10)
    assert len(result) == 10  # bug: 13
