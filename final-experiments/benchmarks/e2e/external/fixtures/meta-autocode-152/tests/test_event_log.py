import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from event_log import get_recent_events

# PASS (bug and fix agree)

def test_empty_list():
    assert get_recent_events([], 3) == []

def test_zero_count():
    assert get_recent_events([1, 2, 3], 0) == []

def test_n_larger_than_list():
    assert get_recent_events([1, 2, 3], 10) == [1, 2, 3]  # both return full list

def test_exact_length():
    assert get_recent_events([1, 2, 3], 3) == [1, 2, 3]  # both return all

# FAIL (bug returns first N, fix should return last N)

def test_last_three_of_five():
    result = get_recent_events([1, 2, 3, 4, 5], 3)
    assert result == [3, 4, 5]  # bug: [1,2,3]

def test_last_two_of_four():
    result = get_recent_events([10, 20, 30, 40], 2)
    assert result == [30, 40]  # bug: [10,20]

def test_last_one():
    result = get_recent_events([1, 2, 3, 4, 5], 1)
    assert result == [5]  # bug: [1]
