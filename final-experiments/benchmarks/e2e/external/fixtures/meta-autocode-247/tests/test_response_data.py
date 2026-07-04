import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from response_data import get_response_data

# PASS with bug (no 'data' key or 'data': None — both return None)
def test_empty():
    assert get_response_data({}) is None

def test_status_only():
    assert get_response_data({'status': 200}) is None

def test_headers_only():
    assert get_response_data({'headers': {}}) is None

def test_data_none():
    assert get_response_data({'data': None}) is None

# FAIL with bug (has non-None 'data' — bug reads 'payload', returns None)
def test_data_dict():
    assert get_response_data({'data': {'id': 1}}) == {'id': 1}

def test_data_list():
    assert get_response_data({'data': [1, 2, 3], 'status': 200}) == [1, 2, 3]

def test_data_string():
    assert get_response_data({'data': 'ok'}) == 'ok'
