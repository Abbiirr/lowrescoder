import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from metrics_calculator import calculate_percentage

# PASS (evenly divisible — // and / agree)

def test_zero_percent():
    assert calculate_percentage(0, 100) == 0

def test_fifty_percent():
    assert calculate_percentage(50, 100) == 50

def test_full_hundred():
    assert calculate_percentage(100, 100) == 100

def test_quarter():
    assert calculate_percentage(25, 100) == 25

# FAIL (fractional result truncated by //)

def test_one_third():
    result = calculate_percentage(1, 3)
    assert abs(result - 33.33) < 0.01  # bug: 33 → abs(33-33.33)=0.33, not < 0.01

def test_two_thirds():
    result = calculate_percentage(2, 3)
    assert abs(result - 66.67) < 0.01  # bug: 66 → abs(66-66.67)=0.67, not < 0.01

def test_one_sixth():
    result = calculate_percentage(1, 6)
    assert abs(result - 16.67) < 0.01  # bug: 16 → abs(16-16.67)=0.67, not < 0.01
