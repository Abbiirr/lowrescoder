import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from query_parser import get_query_string

# PASS (URL contains '?' — both bug and fix return same value)

def test_simple_query():
    assert get_query_string('http://example.com?a=1') == 'a=1'

def test_multi_param():
    assert get_query_string('http://example.com?a=1&b=2') == 'a=1&b=2'

def test_root_query():
    assert get_query_string('/?q=test') == 'q=test'

def test_empty_query():
    assert get_query_string('http://example.com?') == ''

# FAIL (no '?' in URL — bug raises IndexError, fix returns '')

def test_no_query_bare():
    assert get_query_string('http://example.com') == ''  # bug: IndexError

def test_no_query_path():
    assert get_query_string('http://example.com/path') == ''  # bug: IndexError

def test_no_query_root():
    assert get_query_string('/') == ''  # bug: IndexError
