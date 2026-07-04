import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from query_list import parse_list_query_param

def test_single_value():
    assert parse_list_query_param('tag=python', 'tag') == ['python']

def test_no_matching_param():
    assert parse_list_query_param('other=val', 'tag') == []

def test_empty_string():
    assert parse_list_query_param('', 'tag') == []

def test_unrelated_params_ignored():
    assert parse_list_query_param('x=1&y=2', 'tag') == []

def test_multiple_values():
    # BUG: only last value kept → ['c'] instead of ['a','b','c']
    assert parse_list_query_param('tag=a&tag=b&tag=c', 'tag') == ['a', 'b', 'c']

def test_two_values():
    # BUG: only 'rust' kept, 'python' lost
    assert parse_list_query_param('tag=python&tag=rust', 'tag') == ['python', 'rust']

def test_mixed_params_with_list():
    # BUG: only 'b' kept for tag
    assert parse_list_query_param('x=1&tag=a&y=2&tag=b', 'tag') == ['a', 'b']
