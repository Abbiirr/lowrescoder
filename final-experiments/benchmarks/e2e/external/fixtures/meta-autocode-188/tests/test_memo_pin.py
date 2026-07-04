import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from memo_pin import is_pinned

# PASS (no 'is_pinned': True present — bug and fix both return False)

def test_empty_memo():
    assert is_pinned({}) == False

def test_not_pinned():
    assert is_pinned({'is_pinned': False}) == False

def test_both_false():
    assert is_pinned({'pinned': False, 'is_pinned': False}) == False

def test_only_pinned_false():
    assert is_pinned({'pinned': False}) == False

# FAIL ('is_pinned': True present — bug reads wrong key, returns False)

def test_is_pinned_true():
    assert is_pinned({'is_pinned': True}) == True  # bug: False (reads 'pinned' = None)

def test_pinned_false_is_pinned_true():
    assert is_pinned({'is_pinned': True, 'pinned': False}) == True  # bug: False

def test_is_pinned_true_with_id():
    assert is_pinned({'id': 123, 'is_pinned': True}) == True  # bug: False
