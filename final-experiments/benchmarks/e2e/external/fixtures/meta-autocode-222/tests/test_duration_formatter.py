import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from duration_formatter import format_duration

# PASS (seconds < 3600 — minutes don't overflow, bug and fix agree)

def test_zero():
    assert format_duration(0) == '0h 0m 0s'

def test_under_one_minute():
    assert format_duration(59) == '0h 0m 59s'

def test_ninety_seconds():
    assert format_duration(90) == '0h 1m 30s'

def test_just_under_one_hour():
    assert format_duration(3599) == '0h 59m 59s'

# FAIL (seconds >= 3600 — bug reports total minutes, fix reports remainder)

def test_exactly_one_hour():
    assert format_duration(3600) == '1h 0m 0s'  # bug: '1h 60m 0s'

def test_two_hours():
    assert format_duration(7200) == '2h 0m 0s'  # bug: '2h 120m 0s'

def test_one_hour_one_minute():
    assert format_duration(3660) == '1h 1m 0s'  # bug: '1h 61m 0s'
