import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from collection_utils import all_unique

# PASS (has duplicates — both return False correctly)

def test_simple_duplicate():
    assert all_unique([1, 2, 1]) == False

def test_adjacent_duplicate():
    assert all_unique([1, 1]) == False

def test_later_duplicate():
    assert all_unique([1, 2, 1, 3]) == False

def test_all_same():
    assert all_unique([3, 3, 3]) == False

# FAIL (all unique — bug returns None, fix returns True)

def test_empty_list():
    assert all_unique([]) == True  # bug: None (no loop runs, falls off end)

def test_single_item():
    assert all_unique([1]) == True  # bug: None

def test_all_different():
    assert all_unique([1, 2, 3]) == True  # bug: None
