import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from list_dedup import deduplicate

# PASS (no duplicates — bug and fix agree)

def test_empty():
    assert deduplicate([]) == []

def test_single_item():
    assert deduplicate([1]) == [1]

def test_all_unique():
    assert deduplicate([1, 2, 3]) == [1, 2, 3]

def test_all_unique_strings():
    assert deduplicate(['a', 'b', 'c']) == ['a', 'b', 'c']

# FAIL (has duplicates — bug keeps them, fix removes them)

def test_adjacent_duplicate():
    assert deduplicate([1, 1, 2]) == [1, 2]  # bug: [1,1,2]

def test_non_adjacent_duplicate():
    assert deduplicate([1, 2, 1]) == [1, 2]  # bug: [1,2,1]

def test_all_same():
    assert deduplicate([1, 1, 1]) == [1]  # bug: [1,1,1]
