import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from branch_abbreviator import abbreviate_branch

# PASS (name within max_len — no truncation needed)

def test_short_name():
    assert abbreviate_branch('main') == 'main'

def test_feature_branch():
    assert abbreviate_branch('feature/login') == 'feature/login'

def test_exact_max_len():
    assert abbreviate_branch('a' * 20) == 'a' * 20

def test_empty():
    assert abbreviate_branch('') == ''

# FAIL (name exceeds max_len — bug truncates without '...', fix appends '...')

def test_long_repeated():
    assert abbreviate_branch('a' * 25) == 'a' * 17 + '...'  # bug: 'a'*20

def test_long_feature():
    assert abbreviate_branch('feature/very-long-name-that-exceeds') == 'feature/very-long...'  # bug: 'feature/very-long-na'

def test_long_release():
    assert abbreviate_branch('release/2026.06.26-hotfix') == 'release/2026.06.2...'  # bug: 'release/2026.06.26-h'
