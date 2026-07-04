import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from branch_info import get_default_branch

# PASS (no 'default_branch' key, or both keys return same value)

def test_empty():
    assert get_default_branch({}) == 'main'

def test_name_only():
    assert get_default_branch({'name': 'repo'}) == 'main'

def test_both_same():
    assert get_default_branch({'default': 'main', 'default_branch': 'main'}) == 'main'

def test_default_key_main():
    assert get_default_branch({'default': 'main'}) == 'main'

# FAIL ('default_branch' has non-default value — bug returns 'main' or wrong branch)

def test_master():
    assert get_default_branch({'default_branch': 'master'}) == 'master'  # bug: 'main'

def test_develop():
    assert get_default_branch({'default_branch': 'develop', 'name': 'repo'}) == 'develop'  # bug: 'main'

def test_release():
    assert get_default_branch({'default_branch': 'release', 'default': 'main'}) == 'release'  # bug: 'main'
