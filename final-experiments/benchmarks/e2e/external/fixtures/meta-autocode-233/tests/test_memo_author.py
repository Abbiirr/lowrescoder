import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from memo_author import get_memo_author

# PASS (no 'author' key — both bug and fix return None)

def test_empty():
    assert get_memo_author({}) is None

def test_no_author_key():
    assert get_memo_author({'content': 'hi'}) is None

def test_creator_no_username():
    assert get_memo_author({'creator': {}}) is None

def test_creator_name_field():
    assert get_memo_author({'creator': {'name': 'alice'}}) is None

# FAIL ('author' present with 'username' — bug returns None, fix returns username)

def test_author_alice():
    assert get_memo_author({'author': {'username': 'alice'}}) == 'alice'  # bug: None

def test_author_with_id():
    assert get_memo_author({'author': {'username': 'bob'}, 'id': 1}) == 'bob'  # bug: None

def test_author_with_content():
    assert get_memo_author({'author': {'username': 'carol'}, 'content': 'hi'}) == 'carol'  # bug: None
