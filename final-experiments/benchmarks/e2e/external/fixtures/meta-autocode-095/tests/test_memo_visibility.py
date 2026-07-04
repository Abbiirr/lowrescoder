import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from memo_visibility import can_view_memo

# PASS with bug

def test_public_memo_visible_to_all():
    memo = {'visibility': 'public'}
    assert can_view_memo(memo, 'public') is True

def test_protected_visible_to_member():
    memo = {'visibility': 'protected'}
    assert can_view_memo(memo, 'member') is True

def test_protected_visible_to_admin():
    memo = {'visibility': 'protected'}
    assert can_view_memo(memo, 'admin') is True

def test_private_only_admin():
    memo = {'visibility': 'private'}
    assert can_view_memo(memo, 'member') is False

# FAIL with bug ('public' role incorrectly allowed for protected)

def test_protected_not_visible_to_public_role():
    memo = {'visibility': 'protected'}
    assert can_view_memo(memo, 'public') is False  # bug: True

def test_protected_default_visibility_public_role():
    memo = {}  # defaults to 'private' actually... let me make it explicit
    memo = {'visibility': 'protected', 'content': 'secret'}
    assert can_view_memo(memo, 'public') is False  # bug: True

def test_protected_memo_public_role_blocked():
    memo = {'id': 42, 'visibility': 'protected'}
    assert can_view_memo(memo, 'public') is False  # bug: True
