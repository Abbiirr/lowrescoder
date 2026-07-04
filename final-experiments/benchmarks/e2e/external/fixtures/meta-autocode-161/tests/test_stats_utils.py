import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from stats_utils import find_mode

# PASS (bug and fix agree)

def test_empty():
    assert find_mode([]) is None

def test_single_item():
    assert find_mode([5]) == 5  # only one item — both return 5

def test_all_same():
    assert find_mode([3, 3, 3]) == 3  # all count=3, min==max → same result

def test_equal_counts():
    result = find_mode([1, 2])  # both count=1 — min/max pick same (first insertion)
    assert result == 1  # insertion order: 1 first, so both min and max return 1

# FAIL (clear winner — bug returns loser)

def test_one_winner():
    assert find_mode([1, 2, 2]) == 2  # bug: min count → 1 (count=1)

def test_clear_leader():
    assert find_mode([3, 3, 3, 4, 4]) == 3  # bug: min count → 4 (count=2)

def test_tail_heavy():
    assert find_mode([5, 6, 6, 6]) == 6  # bug: min count → 5 (count=1)
