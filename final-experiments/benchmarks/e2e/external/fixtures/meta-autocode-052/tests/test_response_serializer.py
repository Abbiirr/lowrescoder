import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from response_serializer import serialize_response

# --- PASS with bug (exclude_none=False or no None values — bug and fix agree) ---

def test_no_none_exclude_none_true():
    # No None values present — excluding None changes nothing
    data = {'a': 1, 'b': 'hello', 'c': True}
    assert serialize_response(data, exclude_none=True) == {'a': 1, 'b': 'hello', 'c': True}

def test_include_none_when_exclude_false():
    data = {'a': None, 'b': 2}
    assert serialize_response(data, exclude_none=False) == {'a': None, 'b': 2}

def test_empty_dict():
    assert serialize_response({}, exclude_none=True) == {}

def test_non_dict_passthrough():
    assert serialize_response('plain string') == 'plain string'

# --- FAIL with bug (exclude_none=True but bug keeps None values) ---

def test_exclude_single_none():
    data = {'a': None, 'b': 2}
    assert serialize_response(data, exclude_none=True) == {'b': 2}

def test_exclude_all_none():
    data = {'a': None, 'b': None}
    assert serialize_response(data, exclude_none=True) == {}

def test_exclude_none_mixed_types():
    data = {'x': 0, 'y': None, 'z': 'ok', 'w': False}
    assert serialize_response(data, exclude_none=True) == {'x': 0, 'z': 'ok', 'w': False}
