import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from session_expiry import is_session_expired

# PASS with bug (elapsed is clearly within or clearly beyond any ttl)

def test_just_created_not_expired():
    assert is_session_expired(1000, 1010) is False  # 10s elapsed, bug: 10>30 → False

def test_very_old_session_expired():
    assert is_session_expired(0, 9000) is True  # 9000s >> 30s or 1800s

def test_elapsed_over_bug_threshold():
    assert is_session_expired(1000, 1100) is True  # 100s > 30 (bug) → True

def test_custom_ttl_no_expiry():
    assert is_session_expired(0, 5, ttl_minutes=10) is False  # 5 < 10 (bug) → False

# FAIL with bug (elapsed is 31-1799s: correct for 1800s ttl, wrong for 30s bug)

def test_fifty_seconds_not_expired():
    assert is_session_expired(0, 50) is False  # bug: 50>30 → True

def test_twenty_nine_minutes_not_expired():
    assert is_session_expired(0, 1740) is False  # bug: 1740>30 → True

def test_exactly_thirty_minutes_not_expired():
    assert is_session_expired(0, 1800) is False  # bug: 1800>30 → True
