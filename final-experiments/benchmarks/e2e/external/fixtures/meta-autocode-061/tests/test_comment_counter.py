import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from comment_counter import count_issue_comments

def top(id_):
    return {'id': id_, 'body': 'comment', 'parent_id': None}

def reply(id_, parent):
    return {'id': id_, 'body': 'reply', 'parent_id': parent}

# --- PASS with bug (no replies — both agree) ---

def test_empty():
    assert count_issue_comments([]) == 0

def test_two_top_level():
    assert count_issue_comments([top(1), top(2)]) == 2

def test_single_top_level():
    assert count_issue_comments([top(1)]) == 1

def test_three_top_level():
    assert count_issue_comments([top(1), top(2), top(3)]) == 3

# --- FAIL with bug (replies present — bug overcounts) ---

def test_replies_excluded():
    comments = [top(1), reply(2, 1), reply(3, 1)]
    assert count_issue_comments(comments) == 1

def test_all_replies():
    comments = [reply(1, 0), reply(2, 0)]
    assert count_issue_comments(comments) == 0

def test_mixed_top_and_replies():
    comments = [top(1), top(2), reply(3, 1), top(4), reply(5, 2)]
    assert count_issue_comments(comments) == 3
