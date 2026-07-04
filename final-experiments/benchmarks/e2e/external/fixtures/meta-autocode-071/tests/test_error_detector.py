import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from error_detector import is_error_response

# --- PASS with bug (2xx or 5xx — both agree) ---

def test_200_not_error():
    assert is_error_response(200) is False

def test_500_is_error():
    assert is_error_response(500) is True

def test_201_not_error():
    assert is_error_response(201) is False

def test_503_is_error():
    assert is_error_response(503) is True

# --- FAIL with bug (4xx: bug False because < 500, fix True because not 2xx) ---

def test_400_is_error():
    assert is_error_response(400) is True

def test_404_is_error():
    assert is_error_response(404) is True

def test_403_is_error():
    assert is_error_response(403) is True
