import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from list_merger import merge_unique

# PASS (no overlapping items — concatenation equals merged unique set)

def test_disjoint():
    assert merge_unique([1, 2], [3, 4]) == [1, 2, 3, 4]

def test_empty_first():
    assert merge_unique([], [1, 2]) == [1, 2]

def test_empty_second():
    assert merge_unique([1], []) == [1]

def test_both_empty():
    assert merge_unique([], []) == []

# FAIL (overlapping items — bug keeps duplicates, fix removes them)

def test_partial_overlap():
    assert merge_unique([1, 2], [2, 3]) == [1, 2, 3]  # bug: [1,2,2,3]

def test_duplicate_in_first():
    assert merge_unique([1, 1], [1, 2]) == [1, 2]  # bug: [1,1,1,2]

def test_all_overlap():
    assert merge_unique([1, 2, 3], [1, 2]) == [1, 2, 3]  # bug: [1,2,3,1,2]
