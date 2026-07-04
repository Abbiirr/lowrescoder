import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from watcher_counter import count_watchers

# PASS (watchers_count absent or zero — bug and fix both return 0)

def test_empty():
    assert count_watchers({}) == 0

def test_no_watcher_key():
    assert count_watchers({'name': 'repo'}) == 0

def test_watchers_zero():
    assert count_watchers({'watchers_count': 0}) == 0

def test_stargazers_zero():
    assert count_watchers({'stargazers_count': 0}) == 0

# FAIL (watchers_count present and non-zero — bug reads wrong key)

def test_watchers_five():
    assert count_watchers({'watchers_count': 5}) == 5  # bug: 0

def test_watchers_vs_stars():
    assert count_watchers({'watchers_count': 10, 'stargazers_count': 50}) == 10  # bug: 50

def test_watchers_three():
    assert count_watchers({'watchers_count': 3, 'name': 'r'}) == 3  # bug: 0
