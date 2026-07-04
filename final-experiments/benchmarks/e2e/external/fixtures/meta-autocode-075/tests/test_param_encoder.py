import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from param_encoder import encode_params

# --- PASS with bug (no lists or single-item list — both agree) ---

def test_simple_scalar_params():
    result = encode_params({'page': 1, 'limit': 10})
    assert 'page=1' in result and 'limit=10' in result

def test_empty_params():
    assert encode_params({}) == ''

def test_single_string_param():
    assert encode_params({'name': 'alice'}) == 'name=alice'

def test_single_item_list():
    # join(['42']) == '42' and repeat gives 'ids=42' — same result
    assert encode_params({'ids': [42]}) == 'ids=42'

# --- FAIL with bug (multi-value list: bug comma-joins, fix repeats) ---

def test_list_repeated_key():
    result = encode_params({'ids': [1, 2, 3]})
    assert result == 'ids=1&ids=2&ids=3'

def test_list_two_string_values():
    result = encode_params({'tag': ['python', 'web']})
    assert result == 'tag=python&tag=web'

def test_mixed_list_and_scalar():
    result = encode_params({'ids': [1, 2], 'page': 1})
    assert 'ids=1&ids=2' in result
    assert 'page=1' in result
