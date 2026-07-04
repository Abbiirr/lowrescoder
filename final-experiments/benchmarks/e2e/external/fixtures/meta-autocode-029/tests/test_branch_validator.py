import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from branch_validator import is_valid_branch_name

def test_simple_alphanumeric():
    assert is_valid_branch_name("feature") is True

def test_hyphenated_branch():
    assert is_valid_branch_name("fix-null-pointer") is True

def test_invalid_space():
    assert is_valid_branch_name("feat branch") is False

def test_invalid_double_dot():
    assert is_valid_branch_name("feat..main") is False

def test_version_branch_with_dot():
    # BUG: "v1.0" contains '.' so the buggy guard rejects it incorrectly
    assert is_valid_branch_name("v1.0") is True

def test_path_style_with_dot():
    # BUG: "hotfix/fix-1.5" rejected because of '.'
    assert is_valid_branch_name("hotfix/fix-1.5") is True

def test_dotfile_style_branch():
    # BUG: "release.2026" rejected because of '.'
    assert is_valid_branch_name("release.2026") is True
