import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from stash_info import get_stash_count

# PASS (no 'entries' key or entries == 0 — bug and fix both return 0)

def test_empty():
    assert get_stash_count({}) == 0

def test_name_only():
    assert get_stash_count({'name': 'stash'}) == 0

def test_entries_zero():
    assert get_stash_count({'entries': 0}) == 0

def test_count_zero_entries_zero():
    assert get_stash_count({'count': 0, 'entries': 0}) == 0

# FAIL ('entries' key has non-zero value — bug returns 0 or wrong count)

def test_entries_three():
    assert get_stash_count({'entries': 3}) == 3  # bug: 0

def test_entries_with_name():
    assert get_stash_count({'entries': 5, 'name': 'wip'}) == 5  # bug: 0

def test_entries_vs_count():
    assert get_stash_count({'entries': 1, 'count': 0}) == 1  # bug: 0
