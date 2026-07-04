import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from health_checker import is_healthy

# PASS (clearly healthy or clearly unhealthy — bug and fix agree)

def test_perfect():
    assert is_healthy(100.0) == True

def test_high_uptime():
    assert is_healthy(99.9) == True

def test_low_uptime():
    assert is_healthy(98.0) == False

def test_very_low():
    assert is_healthy(95.0) == False

# FAIL (99.0-99.4 range — bug accepts as healthy, fix rejects)

def test_exactly_99():
    assert is_healthy(99.0) == False  # bug: True (99 >= 99)

def test_99_2():
    assert is_healthy(99.2) == False  # bug: True (99.2 >= 99)

def test_99_4():
    assert is_healthy(99.4) == False  # bug: True (99.4 >= 99)
