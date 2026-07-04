import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from param_validator import is_in_range

# PASS (values clearly inside range or outside — bug and fix agree)

def test_middle_of_range():
    assert is_in_range(5, 0, 10) == True

def test_at_minimum():
    assert is_in_range(0, 0, 10) == True

def test_below_minimum():
    assert is_in_range(-1, 0, 10) == False

def test_above_maximum():
    assert is_in_range(11, 0, 10) == False

# FAIL (exactly at max — bug returns False, fix returns True)

def test_at_maximum():
    assert is_in_range(10, 0, 10) == True  # bug: False (10 < 10 is False)

def test_single_point_range():
    assert is_in_range(5, 5, 5) == True  # bug: False (5 < 5 is False)

def test_at_large_max():
    assert is_in_range(100, 0, 100) == True  # bug: False
