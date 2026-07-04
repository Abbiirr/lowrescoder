import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from url_builder import build_query_string

# PASS with bug (empty or single param — no separator needed)

def test_empty_params():
    assert build_query_string({}) == ''

def test_single_param():
    result = build_query_string({'key': 'value'})
    assert result == '?key=value'

def test_starts_with_question_mark():
    result = build_query_string({'a': '1'})
    assert result.startswith('?')

def test_single_numeric_value():
    result = build_query_string({'page': 2})
    assert result == '?page=2'

# FAIL with bug (multiple params reveal &amp; vs & separator)

def test_two_params_separator():
    result = build_query_string({'a': '1', 'b': '2'})
    assert '&amp;' not in result  # bug: &amp; is in result

def test_correct_ampersand():
    result = build_query_string({'x': '1', 'y': '2'})
    assert '&' in result and '&amp;' not in result  # bug: has &amp;

def test_three_params():
    result = build_query_string({'a': 1, 'b': 2, 'c': 3})
    assert result.count('&') == 2 and '&amp;' not in result  # bug: 0 & and 2 &amp;
