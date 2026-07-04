import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from memo_visibility import filter_by_visibility

MEMOS = [
    {'id': 1, 'content': 'hello', 'visibility': 'PUBLIC'},
    {'id': 2, 'content': 'secret', 'visibility': 'PRIVATE'},
    {'id': 3, 'content': 'friends only', 'visibility': 'PROTECTED'},
    {'id': 4, 'content': 'world', 'visibility': 'PUBLIC'},
    {'id': 5, 'content': 'diary', 'visibility': 'PRIVATE'},
]

def test_filter_public_uppercase():
    result = filter_by_visibility(MEMOS, 'PUBLIC')
    assert [m['id'] for m in result] == [1, 4]

def test_filter_private_uppercase():
    result = filter_by_visibility(MEMOS, 'PRIVATE')
    assert [m['id'] for m in result] == [2, 5]

def test_filter_no_match():
    assert filter_by_visibility(MEMOS, 'DELETED') == []

def test_filter_protected_uppercase():
    result = filter_by_visibility(MEMOS, 'PROTECTED')
    assert [m['id'] for m in result] == [3]

def test_filter_public_lowercase():
    # BUG: 'public' != 'PUBLIC' → returns [] instead of [1,4]
    result = filter_by_visibility(MEMOS, 'public')
    assert [m['id'] for m in result] == [1, 4]

def test_filter_private_mixed_case():
    # BUG: 'Private' != 'PRIVATE' → returns []
    result = filter_by_visibility(MEMOS, 'Private')
    assert [m['id'] for m in result] == [2, 5]

def test_filter_protected_lowercase():
    # BUG: 'protected' != 'PROTECTED' → returns []
    result = filter_by_visibility(MEMOS, 'protected')
    assert [m['id'] for m in result] == [3]
