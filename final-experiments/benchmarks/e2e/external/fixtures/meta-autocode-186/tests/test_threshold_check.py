import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from threshold_check import is_response_ok

# PASS (clearly within or over threshold — bug and fix agree)

def test_well_within():
    assert is_response_ok(100, 500) == True

def test_zero_response():
    assert is_response_ok(0, 500) == True

def test_over_threshold():
    assert is_response_ok(600, 500) == False

def test_far_over():
    assert is_response_ok(1000, 500) == False

# FAIL (exactly at threshold — bug True, fix False)

def test_exactly_at_threshold():
    assert is_response_ok(500, 500) == False  # bug: True (500 <= 500)

def test_equal_small():
    assert is_response_ok(100, 100) == False  # bug: True

def test_equal_medium():
    assert is_response_ok(200, 200) == False  # bug: True
