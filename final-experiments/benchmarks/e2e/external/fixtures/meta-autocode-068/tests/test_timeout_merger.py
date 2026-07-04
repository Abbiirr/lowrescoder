import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from timeout_merger import resolve_request_timeout

# --- PASS with bug (no request_timeout — both return instance_timeout) ---

def test_no_request_timeout_uses_instance():
    assert resolve_request_timeout(5000, None) == 5000

def test_zero_instance_no_request():
    assert resolve_request_timeout(0, None) == 0

def test_large_instance_no_request():
    assert resolve_request_timeout(30000, None) == 30000

def test_none_both():
    assert resolve_request_timeout(None, None) is None

# --- FAIL with bug (request_timeout set — bug ignores, fix returns request_timeout) ---

def test_request_timeout_overrides_instance():
    assert resolve_request_timeout(5000, 1000) == 1000

def test_request_timeout_longer_than_instance():
    assert resolve_request_timeout(1000, 30000) == 30000

def test_request_timeout_zero_overrides():
    # 0 means "no timeout" — must override non-zero instance default
    assert resolve_request_timeout(5000, 0) == 0
