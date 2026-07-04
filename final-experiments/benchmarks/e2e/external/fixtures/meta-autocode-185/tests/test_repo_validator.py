import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from repo_validator import is_valid_repo_name

# PASS (clean names and clearly invalid names — bug and fix agree)

def test_simple_name():
    assert is_valid_repo_name('myrepo') == True

def test_hyphenated_name():
    assert is_valid_repo_name('my-repo') == True

def test_space_in_name():
    assert is_valid_repo_name('my repo') == False

def test_dot_in_name():
    assert is_valid_repo_name('my.repo') == False

# FAIL (slash in name — bug returns True, fix returns False)

def test_slash_in_name():
    assert is_valid_repo_name('my/repo') == False  # bug: True

def test_user_slash_project():
    assert is_valid_repo_name('user/project') == False  # bug: True

def test_short_slash():
    assert is_valid_repo_name('a/b') == False  # bug: True
