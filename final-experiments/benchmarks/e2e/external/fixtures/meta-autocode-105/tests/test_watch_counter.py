import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from watch_counter import update_watch_count

# PASS with bug (return value is correct via len)

def test_watch_increments_count():
    repo = {}
    assert update_watch_count(repo, 'alice', True) == 1

def test_unwatch_decrements_count():
    repo = {'watchers': {'alice'}}
    assert update_watch_count(repo, 'alice', False) == 0

def test_second_watcher_count():
    repo = {'watchers': {'alice'}}
    assert update_watch_count(repo, 'bob', True) == 2

def test_duplicate_watch_no_change():
    repo = {'watchers': {'alice'}}
    assert update_watch_count(repo, 'alice', True) == 1

# FAIL with bug (repo['watch_count'] not updated)

def test_watch_count_field_updated():
    repo = {'watch_count': 0}
    update_watch_count(repo, 'alice', True)
    assert repo['watch_count'] == 1  # bug: still 0

def test_unwatch_decrements_field():
    repo = {'watchers': {'alice'}, 'watch_count': 1}
    update_watch_count(repo, 'alice', False)
    assert repo['watch_count'] == 0  # bug: still 1

def test_watch_count_matches_watchers():
    repo = {'watch_count': 0}
    update_watch_count(repo, 'alice', True)
    update_watch_count(repo, 'bob', True)
    assert repo.get('watch_count') == 2  # bug: still 0
