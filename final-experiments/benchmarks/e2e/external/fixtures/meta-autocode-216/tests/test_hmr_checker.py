import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from hmr_checker import has_hot_reload

# PASS (no 'hot' key or 'hot' is falsy — both bug and fix return False)

def test_empty_config():
    assert has_hot_reload({}) is False

def test_other_keys_only():
    assert has_hot_reload({'port': 3000}) is False

def test_hot_false():
    assert has_hot_reload({'hot': False}) is False

def test_hot_zero():
    assert has_hot_reload({'hot': 0}) is False

# FAIL ('hot' is truthy — bug reads wrong key and returns False)

def test_hot_true():
    assert has_hot_reload({'hot': True}) is True  # bug: False

def test_hot_true_with_port():
    assert has_hot_reload({'hot': True, 'port': 5173}) is True  # bug: False

def test_hot_one():
    assert has_hot_reload({'hot': 1}) is True  # bug: False
