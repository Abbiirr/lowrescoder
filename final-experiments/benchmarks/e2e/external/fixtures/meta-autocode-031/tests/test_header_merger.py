import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from header_merger import merge_request_headers

def test_no_config_headers():
    defaults = {'Accept': 'application/json', 'Content-Type': 'application/json'}
    assert merge_request_headers(defaults, None) == defaults

def test_config_header_only():
    assert merge_request_headers({}, {'X-Custom': 'value'}) == {'X-Custom': 'value'}

def test_config_overrides_default():
    result = merge_request_headers({'Content-Type': 'text/plain'}, {'Content-Type': 'application/json'})
    assert result['Content-Type'] == 'application/json'

def test_all_from_config_no_defaults():
    assert merge_request_headers({}, {'Authorization': 'Bearer tok'}) == {'Authorization': 'Bearer tok'}

def test_empty_config_keeps_defaults():
    # BUG: returns {} instead of defaults
    defaults = {'Accept': 'application/json'}
    assert merge_request_headers(defaults, {}) == defaults

def test_default_not_in_config_preserved():
    # BUG: 'Authorization' default is dropped when config only has Content-Type
    result = merge_request_headers(
        {'Authorization': 'Bearer xyz', 'Accept': 'application/json'},
        {'Content-Type': 'application/json'}
    )
    assert result.get('Authorization') == 'Bearer xyz'

def test_both_unique_headers_merged():
    # BUG: only config headers returned, 'A' from defaults lost
    result = merge_request_headers({'A': '1'}, {'B': '2'})
    assert result == {'A': '1', 'B': '2'}
