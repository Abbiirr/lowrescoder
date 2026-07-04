import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from commit_linter import lint_commit_message

# PASS with bug (invalid cases: unknown type → no error from bug; empty → error)

def test_empty_message_error():
    assert 'message is empty' in lint_commit_message('')

def test_missing_colon_error():
    assert 'missing colon separator' in lint_commit_message('feat add thing')

def test_unknown_type_no_error():
    # Bug: 'random' not in ALLOWED_TYPES → no error appended → []
    # Fix: 'random' not in ALLOWED_TYPES → append error
    # So this test PASSES with bug (empty list == empty list)
    assert lint_commit_message('random: something') == []  # bug: [] — but this should be [error]!

def test_returns_list():
    assert isinstance(lint_commit_message('feat: add button'), list)

# FAIL with bug (valid types incorrectly flagged as errors)

def test_feat_type_valid():
    assert lint_commit_message('feat: add button') == []  # bug: ['unknown commit type: feat']

def test_fix_type_valid():
    assert lint_commit_message('fix: null pointer') == []  # bug: ['unknown commit type: fix']

def test_chore_type_valid():
    assert lint_commit_message('chore: update deps') == []  # bug: ['unknown commit type: chore']
