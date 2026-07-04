import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from http_validator import is_valid_method

# PASS (already uppercase — bug and fix agree)

def test_get_uppercase():
    assert is_valid_method('GET') == True

def test_post_uppercase():
    assert is_valid_method('POST') == True

def test_delete_uppercase():
    assert is_valid_method('DELETE') == True

def test_invalid_method():
    assert is_valid_method('FETCH') == False  # both False

# FAIL (lowercase/mixed — bug: False, fix: True)

def test_get_lowercase():
    assert is_valid_method('get') == True  # bug: 'get' not in set → False

def test_post_lowercase():
    assert is_valid_method('post') == True  # bug: False

def test_put_mixed_case():
    assert is_valid_method('Put') == True  # bug: False
