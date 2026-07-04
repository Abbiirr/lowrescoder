import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from head_checker import is_detached_head

# PASS (no 'is_detached' or it is falsy — both bug and fix return False)

def test_empty():
    assert is_detached_head({}) is False

def test_on_branch():
    assert is_detached_head({'branch': 'main'}) is False

def test_is_detached_false():
    assert is_detached_head({'is_detached': False}) is False

def test_is_detached_zero():
    assert is_detached_head({'is_detached': 0}) is False

# FAIL ('is_detached' truthy — bug reads wrong key and returns False)

def test_is_detached_true():
    assert is_detached_head({'is_detached': True}) is True  # bug: False

def test_is_detached_with_hash():
    assert is_detached_head({'is_detached': True, 'hash': 'abc1234'}) is True  # bug: False

def test_is_detached_one():
    assert is_detached_head({'is_detached': 1}) is True  # bug: False
