import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from commit_checker import is_conventional_commit

# PASS (lowercase types and clearly non-conventional — bug and fix agree)

def test_feat():
    assert is_conventional_commit('feat: add login') == True

def test_fix():
    assert is_conventional_commit('fix: resolve crash') == True

def test_no_colon():
    assert is_conventional_commit('random commit message') == False

def test_wrong_format():
    assert is_conventional_commit('initial setup') == False

# FAIL (mixed-case type — bug returns False, fix returns True)

def test_capitalised_feat():
    assert is_conventional_commit('Feat: add login') == True  # bug: False

def test_uppercase_fix():
    assert is_conventional_commit('FIX: resolve crash') == True  # bug: False

def test_mixed_docs():
    assert is_conventional_commit('Docs: update readme') == True  # bug: False
