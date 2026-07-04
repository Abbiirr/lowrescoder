import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from response_time import calculate_avg_response_time

def test_empty_list():
    assert calculate_avg_response_time([]) == 0

def test_all_positive():
    assert calculate_avg_response_time([100, 200, 300]) == 200

def test_single_value():
    assert calculate_avg_response_time([500]) == 500

def test_single_zero_returns_zero():
    # All failed → no data → avg is 0 (same result buggy or fixed)
    assert calculate_avg_response_time([0]) == 0

def test_zeros_excluded_from_avg():
    # BUG: (100+200+0)/3 = 100 — should be (100+200)/2 = 150
    assert calculate_avg_response_time([100, 200, 0]) == 150

def test_heavy_failures():
    # BUG: (0+0+0+100)/4 = 25 — should be 100/1 = 100
    assert calculate_avg_response_time([0, 0, 0, 100]) == 100

def test_mixed_zeros_and_values():
    # BUG: (50+0+150)/3 ≈ 66.67 — should be (50+150)/2 = 100
    assert calculate_avg_response_time([50, 0, 150]) == 100
