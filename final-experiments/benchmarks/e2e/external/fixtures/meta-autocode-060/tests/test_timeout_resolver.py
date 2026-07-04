import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from timeout_resolver import resolve_timeout

# --- PASS with bug (positive timeouts — bug and fix agree) ---

def test_positive_60():
    assert resolve_timeout(60) == 60

def test_positive_300():
    assert resolve_timeout(300) == 300

def test_one_second():
    assert resolve_timeout(1) == 1

def test_exactly_default():
    assert resolve_timeout(30) == 30

# --- FAIL with bug (zero / negative → bug returns raw, fix returns DEFAULT_TIMEOUT=30) ---

def test_zero_uses_default():
    assert resolve_timeout(0) == 30

def test_negative_one_uses_default():
    assert resolve_timeout(-1) == 30

def test_large_negative_uses_default():
    assert resolve_timeout(-100) == 30
