import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from notification_filter import filter_notifications

NOTIFS = [
    {'id': 1, 'read': False, 'title': 'PR opened'},
    {'id': 2, 'read': True, 'title': 'Issue closed'},
    {'id': 3, 'read': False, 'title': 'Mention'},
]

# PASS with bug

def test_no_filter_returns_all():
    assert len(filter_notifications(NOTIFS)) == 3

def test_empty_input():
    assert filter_notifications([]) == []

def test_all_unread_but_filter_off():
    notifs = [{'read': False}] * 3
    assert len(filter_notifications(notifs)) == 3

def test_returns_list():
    assert isinstance(filter_notifications(NOTIFS, unread_only=True), list)

# FAIL with bug (unread_only filters for read instead of unread)

def test_unread_only_returns_unread():
    result = filter_notifications(NOTIFS, unread_only=True)
    ids = [n['id'] for n in result]
    assert 1 in ids and 3 in ids  # bug: returns [2] (only read)

def test_unread_only_excludes_read():
    result = filter_notifications(NOTIFS, unread_only=True)
    ids = [n['id'] for n in result]
    assert 2 not in ids  # bug: 2 IS in result

def test_unread_only_count():
    result = filter_notifications(NOTIFS, unread_only=True)
    assert len(result) == 2  # bug: 1 (only the read one)
