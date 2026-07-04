import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from rate_limiter import is_allowed

# PASS with bug (well under limit or testing only blocked calls)

def test_well_under_limit():
    results = [is_allowed('a1', 10, 60, _now=0) for _ in range(3)]
    assert results == [True, True, True]

def test_third_call_blocked():
    # max=2, 3 calls: 3rd blocked with both bug and fix
    results = [is_allowed('a2', 2, 60, _now=0) for _ in range(3)]
    assert results[-1] is False

def test_independent_clients():
    r1 = is_allowed('a3', 10, 60, _now=0)
    r2 = is_allowed('a4', 10, 60, _now=0)
    assert r1 is True and r2 is True

def test_window_reset():
    # Two calls in window, third after window resets
    is_allowed('a5', 5, 60, _now=0)
    is_allowed('a5', 5, 60, _now=0)
    result = is_allowed('a5', 5, 60, _now=100)
    assert result is True

# FAIL with bug (boundary call: the max_requests-th call must succeed)

def test_exactly_at_limit():
    # max=3, all 3 requests should be allowed
    results = [is_allowed('b1', 3, 60, _now=0) for _ in range(3)]
    assert results == [True, True, True]  # bug: [True, True, False]

def test_max_one_allowed():
    # max=1 means 1 request is allowed; bug blocks even the first
    assert is_allowed('b2', 1, 60, _now=0) is True  # bug: False

def test_fifth_of_five_allowed():
    results = [is_allowed('b3', 5, 60, _now=0) for _ in range(5)]
    assert results[-1] is True  # bug: False (5 < 5 is False)
