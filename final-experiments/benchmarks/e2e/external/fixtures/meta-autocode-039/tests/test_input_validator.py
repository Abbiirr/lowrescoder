import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
import pytest
from input_validator import validate_numeric_input

def test_value_within_range():
    validate_numeric_input(5, min_val=0, max_val=10)  # no exception

def test_below_min_raises():
    with pytest.raises(ValueError):
        validate_numeric_input(-1, min_val=0, max_val=10)

def test_no_constraints():
    validate_numeric_input(9999)  # no exception

def test_min_boundary_valid():
    validate_numeric_input(0, min_val=0, max_val=10)  # 0 == min, should be valid

def test_max_boundary_valid():
    # BUG: value=10, max_val=10 → 10 >= 10 raises ValueError — should be valid
    validate_numeric_input(10, min_val=0, max_val=10)

def test_max_exactly_100():
    # BUG: value=100, max_val=100 → raises ValueError — 100 is valid upper bound
    validate_numeric_input(100, min_val=0, max_val=100)

def test_max_equals_value_small():
    # BUG: value=5, max_val=5 → raises ValueError — should be valid
    validate_numeric_input(5, min_val=0, max_val=5)
