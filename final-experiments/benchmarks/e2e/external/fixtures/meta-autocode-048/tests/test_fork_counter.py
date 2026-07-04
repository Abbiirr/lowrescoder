import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from fork_counter import fork_repository

def make_repo(fork_count=0):
    return {'name': 'myrepo', 'fork_count': fork_count, 'star_count': 10, 'description': 'test'}

# --- PASS with bug (fork_count happens to be irrelevant) ---

def test_returns_repo_object():
    repo = make_repo()
    result = fork_repository(repo)
    assert result is repo

def test_name_unchanged():
    repo = make_repo()
    fork_repository(repo)
    assert repo['name'] == 'myrepo'

def test_star_count_unchanged():
    repo = make_repo(fork_count=5)
    fork_repository(repo)
    assert repo['star_count'] == 10

def test_description_unchanged():
    repo = make_repo()
    fork_repository(repo)
    assert repo['description'] == 'test'

# --- FAIL with bug (fork_count should increment) ---

def test_fork_increments_from_zero():
    repo = make_repo(fork_count=0)
    fork_repository(repo)
    assert repo['fork_count'] == 1

def test_fork_increments_from_existing():
    repo = make_repo(fork_count=5)
    fork_repository(repo)
    assert repo['fork_count'] == 6

def test_multiple_forks_accumulate():
    repo = make_repo(fork_count=0)
    fork_repository(repo)
    fork_repository(repo)
    fork_repository(repo)
    assert repo['fork_count'] == 3
