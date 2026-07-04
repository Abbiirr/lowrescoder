import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from memo_visibility import count_public_memos

# PASS (all memos are PUBLIC, or list is empty — bug and fix agree)

def test_empty():
    assert count_public_memos([]) == 0

def test_one_public():
    assert count_public_memos([{'id': 1, 'visibility': 'PUBLIC'}]) == 1

def test_two_public():
    memos = [{'id': 1, 'visibility': 'PUBLIC'}, {'id': 2, 'visibility': 'PUBLIC'}]
    assert count_public_memos(memos) == 2

def test_three_public():
    memos = [{'id': i, 'visibility': 'PUBLIC'} for i in range(3)]
    assert count_public_memos(memos) == 3

# FAIL (private memos present — bug inflates count)

def test_all_private():
    memos = [{'id': 1, 'visibility': 'PRIVATE'}, {'id': 2, 'visibility': 'PRIVATE'}]
    assert count_public_memos(memos) == 0  # bug: 2

def test_mixed_visibility():
    memos = [{'id': 1, 'visibility': 'PUBLIC'}, {'id': 2, 'visibility': 'PRIVATE'}]
    assert count_public_memos(memos) == 1  # bug: 2

def test_single_private():
    assert count_public_memos([{'id': 1, 'visibility': 'PRIVATE'}]) == 0  # bug: 1
