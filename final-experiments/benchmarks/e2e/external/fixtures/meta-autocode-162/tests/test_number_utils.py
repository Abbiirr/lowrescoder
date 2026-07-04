import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from number_utils import digit_sum

# PASS (non-negative — no '-' sign in str())

def test_zero():
    assert digit_sum(0) == 0

def test_single_digit():
    assert digit_sum(5) == 5

def test_multi_digit():
    assert digit_sum(123) == 6

def test_with_zero_digit():
    assert digit_sum(10) == 1

# FAIL (negative — bug raises ValueError on '-')

def test_negative_single():
    assert digit_sum(-5) == 5  # bug: int('-') raises ValueError

def test_negative_multi():
    assert digit_sum(-123) == 6  # bug: ValueError on str(-123) = '-123'

def test_negative_with_zero():
    assert digit_sum(-10) == 1  # bug: ValueError
