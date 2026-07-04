import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from status_checker import is_status_ok

# --- PASS with bug (200 or non-2xx — both agree) ---

def test_200_is_ok():
    assert is_status_ok(200) is True

def test_404_not_ok():
    assert is_status_ok(404) is False

def test_500_not_ok():
    assert is_status_ok(500) is False

def test_301_redirect_not_ok():
    assert is_status_ok(301) is False

# --- FAIL with bug (2xx other than 200 — bug False, fix True) ---

def test_201_created_is_ok():
    assert is_status_ok(201) is True

def test_204_no_content_is_ok():
    assert is_status_ok(204) is True

def test_202_accepted_is_ok():
    assert is_status_ok(202) is True
