import sys, os
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from range_validator import validate_int_range

# --- PASS with bug (value in range, or no bounds — both agree) ---

def test_within_both_bounds():
    assert validate_int_range(50, ge=0, le=100) == 50

def test_no_bounds():
    assert validate_int_range(9999) == 9999

def test_at_lower_bound():
    assert validate_int_range(0, ge=0) == 0

def test_at_upper_bound():
    assert validate_int_range(100, le=100) == 100

# --- FAIL with bug (out of range — bug returns value, fix raises ValueError) ---

def test_below_ge_raises():
    with pytest.raises(ValueError):
        validate_int_range(-1, ge=0)

def test_above_le_raises():
    with pytest.raises(ValueError):
        validate_int_range(101, le=100)

def test_below_lower_bound_both_set():
    with pytest.raises(ValueError):
        validate_int_range(-5, ge=0, le=100)
