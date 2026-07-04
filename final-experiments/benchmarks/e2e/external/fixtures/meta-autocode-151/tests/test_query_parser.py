import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from query_parser import parse_query_string

# PASS (bug and fix agree — no '=' in values)

def test_empty_query():
    assert parse_query_string('') == {}

def test_single_param():
    assert parse_query_string('page=1') == {'page': '1'}

def test_multiple_params():
    assert parse_query_string('a=1&b=2&c=3') == {'a': '1', 'b': '2', 'c': '3'}

def test_empty_value():
    assert parse_query_string('token=') == {'token': ''}

# FAIL (value contains '=' — bug raises ValueError)

def test_value_with_equals():
    result = parse_query_string('token=abc=xyz')
    assert result == {'token': 'abc=xyz'}  # bug: split('=') → too many values to unpack

def test_base64_value():
    result = parse_query_string('data=SGVsbG8=')
    assert result == {'data': 'SGVsbG8='}  # bug: crashes on trailing '='

def test_nested_equals_in_value():
    result = parse_query_string('filter=a=1&sort=desc')
    assert result == {'filter': 'a=1', 'sort': 'desc'}  # bug: crashes on 'filter=a=1'
