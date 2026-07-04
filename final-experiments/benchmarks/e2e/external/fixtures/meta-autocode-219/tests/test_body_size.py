import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from body_size import is_body_too_large

# PASS (clearly under or clearly over — both bug and fix agree)

def test_under_limit():
    assert is_body_too_large('x', 10) is False

def test_empty():
    assert is_body_too_large('', 10) is False

def test_over_limit():
    assert is_body_too_large('x' * 100, 10) is True

def test_over_different_limit():
    assert is_body_too_large('x' * 11, 5) is True

# FAIL (content is exactly at limit — bug says too large, fix says OK)

def test_exactly_at_limit_10():
    assert is_body_too_large('x' * 10, 10) is False  # bug: True

def test_exactly_at_limit_5():
    assert is_body_too_large('hello', 5) is False  # bug: True

def test_exactly_at_limit_3():
    assert is_body_too_large('abc', 3) is False  # bug: True
