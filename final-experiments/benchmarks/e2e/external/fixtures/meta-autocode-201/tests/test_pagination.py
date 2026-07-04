import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from pagination import validate_limit

# PASS (values clearly valid or invalid under both limits)

def test_typical_limit():
    assert validate_limit(10) == True

def test_minimum():
    assert validate_limit(1) == True

def test_zero():
    assert validate_limit(0) == False

def test_negative():
    assert validate_limit(-5) == False

# FAIL (101-1000 — accepted by bug, rejected by fix)

def test_just_over_max():
    assert validate_limit(101) == False  # bug: True

def test_large_value():
    assert validate_limit(500) == False  # bug: True

def test_at_bug_max():
    assert validate_limit(1000) == False  # bug: True
