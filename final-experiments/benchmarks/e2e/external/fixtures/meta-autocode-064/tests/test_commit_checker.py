import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from commit_checker import check_commit_message

# --- PASS with bug (short/empty/over-72 — both agree) ---

def test_short_message_no_warning():
    assert check_commit_message('Add feature') == []

def test_empty_message():
    assert check_commit_message('') == []

def test_exactly_50_chars():
    msg = 'A' * 50
    assert check_commit_message(msg) == []

def test_over_72_warns():
    msg = 'A' * 80
    warnings = check_commit_message(msg)
    assert len(warnings) >= 1

# --- FAIL with bug (51-72 chars: bug silent, fix warns) ---

def test_51_chars_warns():
    msg = 'A' * 51
    warnings = check_commit_message(msg)
    assert len(warnings) >= 1

def test_60_chars_warns():
    msg = 'A' * 60
    warnings = check_commit_message(msg)
    assert len(warnings) >= 1

def test_72_chars_warns():
    msg = 'A' * 72
    warnings = check_commit_message(msg)
    assert len(warnings) >= 1
