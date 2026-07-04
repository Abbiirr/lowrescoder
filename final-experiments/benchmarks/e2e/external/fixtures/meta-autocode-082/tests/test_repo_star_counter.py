import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from repo_star_counter import toggle_star

# PASS with bug

def test_star_increments_count():
    repo = {'stars': 0}
    assert toggle_star(repo, 'alice') == 1

def test_second_user_star():
    repo = {'stars': 1, 'starred_by': {'alice'}}
    assert toggle_star(repo, 'bob') == 2

def test_star_adds_user():
    repo = {'stars': 0}
    toggle_star(repo, 'alice')
    assert 'alice' in repo['starred_by']

def test_unstar_removes_user():
    repo = {'stars': 1, 'starred_by': {'alice'}}
    toggle_star(repo, 'alice')
    assert 'alice' not in repo['starred_by']

# FAIL with bug (unstar increments instead of decrements)

def test_unstar_decrements_count():
    repo = {'stars': 1, 'starred_by': {'alice'}}
    count = toggle_star(repo, 'alice')
    assert count == 0  # bug returns 2

def test_star_then_unstar_returns_zero():
    repo = {'stars': 0}
    toggle_star(repo, 'alice')
    count = toggle_star(repo, 'alice')
    assert count == 0  # bug returns 2

def test_unstar_from_two_gives_one():
    repo = {'stars': 2, 'starred_by': {'alice', 'bob'}}
    count = toggle_star(repo, 'alice')
    assert count == 1  # bug returns 3
