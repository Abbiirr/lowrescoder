import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from response_checker import is_success

# PASS (200 and non-2xx — bug and fix agree)

def test_200_ok():
    assert is_success(200) == True

def test_400_bad_request():
    assert is_success(400) == False

def test_500_server_error():
    assert is_success(500) == False

def test_404_not_found():
    assert is_success(404) == False

# FAIL (other 2xx codes — bug returns False, fix returns True)

def test_201_created():
    assert is_success(201) == True  # bug: False

def test_204_no_content():
    assert is_success(204) == True  # bug: False

def test_206_partial():
    assert is_success(206) == True  # bug: False
