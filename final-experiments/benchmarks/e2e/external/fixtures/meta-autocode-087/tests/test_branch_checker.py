import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from branch_checker import is_valid_branch_name

# PASS with bug

def test_simple_name_valid():
    assert is_valid_branch_name('feature/my-branch') is True

def test_empty_invalid():
    assert is_valid_branch_name('') is False

def test_leading_slash_invalid():
    assert is_valid_branch_name('/bad') is False

def test_trailing_slash_invalid():
    assert is_valid_branch_name('bad/') is False

# FAIL with bug (..) not caught

def test_double_dot_invalid():
    assert is_valid_branch_name('bad..branch') is False  # bug: returns True

def test_double_dot_at_start_invalid():
    assert is_valid_branch_name('..hidden') is False  # bug: returns True

def test_dotlock_with_double_dot_invalid():
    assert is_valid_branch_name('refs/heads/..hidden') is False  # bug: returns True
