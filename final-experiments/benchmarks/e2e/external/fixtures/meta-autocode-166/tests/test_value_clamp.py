import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from value_clamp import clamp

# PASS (value already in range — bug and fix return same value)

def test_in_range():
    assert clamp(5, 0, 10) == 5

def test_at_min_boundary():
    assert clamp(0, 0, 10) == 0

def test_at_max_boundary():
    assert clamp(10, 0, 10) == 10

def test_in_range_offset():
    assert clamp(7, 5, 15) == 7

# FAIL (out of range — bug returns wrong bound)

def test_below_min():
    assert clamp(-1, 0, 10) == 0  # bug: returns max_val=10

def test_above_max():
    assert clamp(15, 0, 10) == 10  # bug: returns min_val=0

def test_far_below_min():
    assert clamp(-5, 2, 8) == 2  # bug: returns max_val=8
