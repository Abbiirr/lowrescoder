import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from response_timer import compute_elapsed_ms

# PASS with bug (symmetric — only tests that elapsed is non-zero pass regardless of sign)

def test_same_timestamp():
    assert compute_elapsed_ms(100.0, 100.0) == 0

def test_returns_milliseconds_unit():
    # Just checks that the multiplier is 1000 (absolute value)
    result = compute_elapsed_ms(1.0, 0.0)
    assert abs(result) == 1000.0

def test_large_gap():
    result = compute_elapsed_ms(200.0, 100.0)
    # Bug: 200-100=100s → 100000ms. Same as correct (100-200 would be -100000).
    # But we only check sign here... wait, 200-100=100 is POSITIVE with bug.
    # Without bug: end-start = 100-200 = -100 → -100000ms.
    # Hmm, 200 start > 100 end means end is BEFORE start. That's backwards.
    # Let me reconsider: start_ts=100, end_ts=200 makes sense (started at 100, ended at 200)
    # Correct: end - start = 200 - 100 = 100s = 100000ms
    # Bug: start - end = 100 - 200 = -100s = -100000ms
    # So test_large_gap with start=200, end=100 actually has end before start (invalid)
    # Let me use start=100, end=200 for valid test
    result = compute_elapsed_ms(100.0, 200.0)
    assert abs(result) == 100000.0  # passes with bug (-100000) and correct (100000)

def test_sub_second():
    result = compute_elapsed_ms(0.0, 0.5)
    assert abs(result) == 500.0

# FAIL with bug (must return positive elapsed, not negative)

def test_positive_elapsed():
    result = compute_elapsed_ms(1000.0, 1001.0)
    assert result == 1000.0  # bug: -1000.0 (start - end)

def test_small_gap():
    result = compute_elapsed_ms(0.0, 0.1)
    assert result == 100.0  # bug: -100.0

def test_typical_request():
    result = compute_elapsed_ms(1700000000.0, 1700000000.25)
    assert result == 250.0  # bug: -250.0
