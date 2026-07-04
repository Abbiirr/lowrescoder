import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from alert_checker import is_stale_alert

# PASS (clearly below or clearly above threshold)

def test_fresh():
    assert is_stale_alert(100, 300) == False

def test_stale():
    assert is_stale_alert(400, 300) == True

def test_zero_age():
    assert is_stale_alert(0, 300) == False

def test_far_over():
    assert is_stale_alert(1000, 300) == True

# FAIL (exactly at max_age — bug False, fix True)

def test_exactly_at_max():
    assert is_stale_alert(300, 300) == True  # bug: False (300 > 300 is False)

def test_equal_small():
    assert is_stale_alert(60, 60) == True  # bug: False

def test_equal_large():
    assert is_stale_alert(3600, 3600) == True  # bug: False
