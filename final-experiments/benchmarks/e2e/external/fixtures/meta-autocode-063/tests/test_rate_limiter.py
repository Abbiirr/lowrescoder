import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from rate_limiter import is_rate_limited

# --- PASS with bug (both agree: clearly under or clearly over limit) ---

def test_well_under_limit():
    assert is_rate_limited(5, 100, []) is False

def test_well_over_limit():
    assert is_rate_limited(150, 100, []) is True

def test_zero_requests():
    assert is_rate_limited(0, 100, []) is False

def test_one_under_limit():
    assert is_rate_limited(99, 100, []) is False

# --- FAIL with bug (exactly at limit — bug allows, fix blocks) ---

def test_exactly_at_limit():
    # request_count == limit: bug (>) returns False (allow), fix (>=) returns True (block)
    assert is_rate_limited(100, 100, []) is True

def test_at_limit_small():
    assert is_rate_limited(10, 10, []) is True

def test_at_limit_one():
    assert is_rate_limited(1, 1, []) is True
