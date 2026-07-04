import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from branch_checker import is_main_branch

# PASS (exactly 'main' and clearly not — bug and fix agree)

def test_main():
    assert is_main_branch('main') == True

def test_develop():
    assert is_main_branch('develop') == False

def test_feature():
    assert is_main_branch('feature/login') == False

def test_master():
    assert is_main_branch('master') == False

# FAIL (starts with 'main' but not equal — bug True, fix False)

def test_mainline():
    assert is_main_branch('mainline') == False  # bug: True

def test_main_branch():
    assert is_main_branch('main-branch') == False  # bug: True

def test_main2():
    assert is_main_branch('main2') == False  # bug: True
