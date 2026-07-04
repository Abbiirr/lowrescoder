import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from memo_sorter import get_latest_memo

# PASS (empty, single, or all-equal timestamps — bug and fix agree)

def test_empty():
    assert get_latest_memo([]) is None

def test_single():
    memo = {'id': 1, 'updated_at': 100}
    assert get_latest_memo([memo]) == memo

def test_equal_timestamps():
    m1 = {'id': 1, 'updated_at': 200}
    m2 = {'id': 2, 'updated_at': 200}
    assert get_latest_memo([m1, m2]) == m1  # stable sort: first element returned

def test_three_equal():
    memos = [{'id': i, 'updated_at': 300} for i in range(3)]
    assert get_latest_memo(memos) == memos[0]

# FAIL (different timestamps — bug returns oldest, fix returns latest)

def test_returns_latest_not_oldest():
    m1 = {'id': 1, 'updated_at': 100}
    m2 = {'id': 2, 'updated_at': 300}
    assert get_latest_memo([m1, m2]) == m2  # bug: m1 (ascending → oldest)

def test_unsorted_input():
    m1 = {'id': 1, 'updated_at': 500}
    m2 = {'id': 2, 'updated_at': 100}
    m3 = {'id': 3, 'updated_at': 300}
    assert get_latest_memo([m1, m2, m3]) == m1  # bug: m2 (ts=100 smallest)

def test_reversed_input():
    m1 = {'id': 1, 'updated_at': 200}
    m2 = {'id': 2, 'updated_at': 100}
    assert get_latest_memo([m1, m2]) == m1  # bug: m2 (ts=100 ascending first)
