import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from rate_limit import get_rate_limit

# PASS with bug (no 'limit' key — both return default 100)
def test_empty():
    assert get_rate_limit({}) == 100

def test_burst_only():
    assert get_rate_limit({'burst': 200}) == 100

def test_window_only():
    assert get_rate_limit({'window': 60}) == 100

def test_limit_matches_default():
    assert get_rate_limit({'limit': 100}) == 100

# FAIL with bug (has 'limit' != 100 — bug reads 'rate', returns 100)
def test_limit_50():
    assert get_rate_limit({'limit': 50}) == 50

def test_limit_200():
    assert get_rate_limit({'limit': 200, 'window': 60}) == 200

def test_limit_500():
    assert get_rate_limit({'limit': 500}) == 500
