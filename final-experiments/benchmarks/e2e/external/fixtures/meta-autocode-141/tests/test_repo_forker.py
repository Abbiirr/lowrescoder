import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from repo_forker import fork_repository

# PASS with bug (fork object creation is correct regardless of fork_count)

def test_fork_has_correct_name():
    repo = {'id': 1, 'name': 'myrepo', 'fork_count': 0}
    fork = fork_repository(repo, user_id=42)
    assert fork['name'] == 'myrepo'

def test_fork_has_correct_owner():
    repo = {'id': 1, 'name': 'x', 'fork_count': 0}
    fork = fork_repository(repo, user_id=99)
    assert fork['owner'] == 99

def test_fork_references_parent():
    repo = {'id': 7, 'name': 'repo', 'fork_count': 0}
    fork = fork_repository(repo, user_id=1)
    assert fork['parent_id'] == 7

def test_fork_starts_with_zero_stars():
    repo = {'id': 1, 'name': 'r', 'fork_count': 0}
    fork = fork_repository(repo, user_id=1)
    assert fork['stars'] == 0

# FAIL with bug (fork_count must increment, not decrement)

def test_fork_count_incremented():
    repo = {'id': 1, 'name': 'r', 'fork_count': 5}
    fork_repository(repo, user_id=1)
    assert repo['fork_count'] == 6  # bug: 4

def test_fork_count_starts_at_zero():
    repo = {'id': 1, 'name': 'r', 'fork_count': 0}
    fork_repository(repo, user_id=1)
    assert repo['fork_count'] == 1  # bug: -1

def test_multiple_forks():
    repo = {'id': 1, 'name': 'r', 'fork_count': 2}
    fork_repository(repo, user_id=1)
    fork_repository(repo, user_id=2)
    assert repo['fork_count'] == 4  # bug: 0
