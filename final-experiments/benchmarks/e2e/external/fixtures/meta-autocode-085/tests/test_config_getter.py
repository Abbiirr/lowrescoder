import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from config_getter import get_nested

# PASS with bug (values are non-None)

def test_top_level_key():
    assert get_nested({'a': 1}, 'a') == 1

def test_nested_two_levels():
    cfg = {'server': {'port': 8080}}
    assert get_nested(cfg, 'server', 'port') == 8080

def test_missing_key_returns_default():
    assert get_nested({'a': 1}, 'b', default='fallback') == 'fallback'

def test_empty_config_returns_default():
    assert get_nested({}, 'key', default=42) == 42

# FAIL with bug (None value with non-None default)

def test_none_value_not_replaced_by_default():
    cfg = {'feature': None}
    result = get_nested(cfg, 'feature', default='MISSING')
    assert result is None  # bug: returns 'MISSING' (treats None value as missing)

def test_nested_none_value_preserved():
    cfg = {'db': {'password': None}}
    result = get_nested(cfg, 'db', 'password', default='secret')
    assert result is None  # bug: returns 'secret'

def test_none_value_distinguished_from_missing():
    cfg = {'opt': {'val': None}}
    present = get_nested(cfg, 'opt', 'val', default=True)
    missing = get_nested(cfg, 'opt', 'nope', default=True)
    # Both should differ: val exists (None), nope is missing (True)
    assert present is None  # bug: returns True — same as missing!
