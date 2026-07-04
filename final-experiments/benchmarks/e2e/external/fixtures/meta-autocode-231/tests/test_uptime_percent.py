import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from uptime_percent import format_uptime_percent

# PASS (total==0 or up==total — both bug and fix return same value)

def test_zero_total():
    assert format_uptime_percent(0, 0) == 0.0

def test_full_uptime_100():
    assert format_uptime_percent(100, 100) == 100.0

def test_full_uptime_3600():
    assert format_uptime_percent(3600, 3600) == 100.0

def test_full_uptime_50():
    assert format_uptime_percent(50, 50) == 100.0

# FAIL (up != total — bug swaps numerator/denominator)

def test_80_percent():
    assert format_uptime_percent(80, 100) == 80.0  # bug: 125.0

def test_90_percent():
    assert format_uptime_percent(9, 10) == 90.0  # bug: 111.1

def test_50_percent():
    assert format_uptime_percent(1, 2) == 50.0  # bug: 200.0
