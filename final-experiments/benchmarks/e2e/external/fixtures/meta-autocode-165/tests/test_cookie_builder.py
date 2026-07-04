import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from cookie_builder import build_cookie_header

# PASS (single or empty — no separator needed, bug and fix agree)

def test_empty():
    assert build_cookie_header({}) == ''

def test_single_cookie():
    assert build_cookie_header({'session': 'abc123'}) == 'session=abc123'

def test_single_empty_value():
    assert build_cookie_header({'token': ''}) == 'token='

def test_single_numeric_value():
    assert build_cookie_header({'count': '0'}) == 'count=0'

# FAIL (multiple cookies — wrong separator ',' instead of '; ')

def test_two_cookies():
    result = build_cookie_header({'a': '1', 'b': '2'})
    assert result == 'a=1; b=2'  # bug: 'a=1,b=2'

def test_three_cookies():
    result = build_cookie_header({'x': 'foo', 'y': 'bar', 'z': 'baz'})
    assert result == 'x=foo; y=bar; z=baz'  # bug: 'x=foo,y=bar,z=baz'

def test_two_real_cookies():
    result = build_cookie_header({'session_id': 'abc', 'csrf': 'xyz'})
    assert result == 'session_id=abc; csrf=xyz'  # bug: 'session_id=abc,csrf=xyz'
