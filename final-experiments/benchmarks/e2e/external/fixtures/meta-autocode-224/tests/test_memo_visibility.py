import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from memo_visibility import is_memo_public

# PASS (non-public visibility — both bug and fix return False)

def test_private():
    assert is_memo_public({'visibility': 'PRIVATE'}) is False

def test_missing_key():
    assert is_memo_public({}) is False

def test_protected():
    assert is_memo_public({'visibility': 'PROTECTED'}) is False

def test_internal():
    assert is_memo_public({'visibility': 'internal'}) is False

# FAIL (visibility is 'PUBLIC' — bug returns False, fix returns True)

def test_public():
    assert is_memo_public({'visibility': 'PUBLIC'}) is True  # bug: False

def test_public_with_id():
    assert is_memo_public({'visibility': 'PUBLIC', 'id': 1}) is True  # bug: False

def test_public_with_content():
    assert is_memo_public({'visibility': 'PUBLIC', 'content': 'hi'}) is True  # bug: False
