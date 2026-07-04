import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from content_truncator import truncate_content

# PASS (content fits — no truncation needed, bug and fix agree)

def test_fits():
    assert truncate_content('hello', 10) == 'hello'

def test_short():
    assert truncate_content('ab', 10) == 'ab'

def test_empty():
    assert truncate_content('', 5) == ''

def test_exact_fit():
    assert truncate_content('hello', 5) == 'hello'

# FAIL (truncation needed — bug produces result longer than max_len)

def test_long_content():
    result = truncate_content('hello world foo', 8)
    assert result == 'hello...'  # bug: 'hello wo...' (11 chars)
    assert len(result) == 8

def test_medium_content():
    result = truncate_content('abcdefghij', 5)
    assert result == 'ab...'  # bug: 'abcde...' (8 chars)
    assert len(result) == 5

def test_max_len_10():
    result = truncate_content('long content here', 10)
    assert result == 'long co...'  # bug: 'long conte...' (13 chars)
    assert len(result) == 10
