import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from dict_utils import have_overlapping_keys

# PASS (identical key sets or completely disjoint — bug and fix agree)

def test_same_single_key():
    assert have_overlapping_keys({'a': 1}, {'a': 2}) == True

def test_same_key_set():
    assert have_overlapping_keys({'a': 1, 'b': 2}, {'b': 3, 'a': 4}) == True

def test_disjoint_single():
    assert have_overlapping_keys({'a': 1}, {'c': 2}) == False

def test_disjoint_different():
    assert have_overlapping_keys({'x': 1}, {'y': 2}) == False

# FAIL (partial overlap — bug returns False because sets differ, fix returns True)

def test_one_extra_key():
    assert have_overlapping_keys({'a': 1}, {'a': 2, 'b': 3}) == True  # bug: False

def test_partial_overlap():
    assert have_overlapping_keys({'a': 1, 'c': 3}, {'a': 2, 'b': 4}) == True  # bug: False

def test_extra_key_other_side():
    assert have_overlapping_keys({'x': 1}, {'x': 2, 'y': 3}) == True  # bug: False
