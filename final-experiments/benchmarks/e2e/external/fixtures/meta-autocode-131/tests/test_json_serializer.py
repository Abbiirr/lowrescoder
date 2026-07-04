import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from json_serializer import serialize_response

# PASS with bug (top-level None excluded correctly)

def test_no_none_values():
    result = json.loads(serialize_response({'a': 1, 'b': 'x'}))
    assert result == {'a': 1, 'b': 'x'}

def test_top_level_none_excluded():
    result = json.loads(serialize_response({'a': 1, 'b': None}))
    assert 'b' not in result

def test_exclude_none_false():
    result = json.loads(serialize_response({'a': 1, 'b': None}, exclude_none=False))
    assert result == {'a': 1, 'b': None}

def test_all_none_excluded():
    result = json.loads(serialize_response({'a': None, 'b': None}))
    assert result == {}

# FAIL with bug (nested None values should also be excluded)

def test_nested_none_excluded():
    data = {'user': {'name': 'Alice', 'email': None}}
    result = json.loads(serialize_response(data))
    # Bug: only top-level; 'user' is not None so it passes through with nested None intact
    nested = result.get('user', {})
    assert 'email' not in nested

def test_nested_dict_none_field():
    data = {'meta': {'version': '1.0', 'deprecated': None}}
    result = json.loads(serialize_response(data))
    assert 'deprecated' not in result.get('meta', {})

def test_deep_nested_none():
    data = {'a': {'b': {'c': None, 'd': 1}}}
    result = json.loads(serialize_response(data))
    assert 'c' not in result['a']['b']
