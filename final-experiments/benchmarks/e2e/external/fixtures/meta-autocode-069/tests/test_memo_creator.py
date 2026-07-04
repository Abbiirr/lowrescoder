import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from memo_creator import create_memo

# --- PASS with bug (explicit visibility set — both agree) ---

def test_explicit_public():
    memo = create_memo('hello', 'public')
    assert memo['visibility'] == 'public'

def test_explicit_private():
    memo = create_memo('hello', 'private')
    assert memo['visibility'] == 'private'

def test_content_preserved():
    memo = create_memo('my note', 'public')
    assert memo['content'] == 'my note'

def test_explicit_protected():
    memo = create_memo('secret', 'protected')
    assert memo['visibility'] == 'protected'

# --- FAIL with bug (no visibility — bug 'public', fix 'private') ---

def test_default_visibility_is_private():
    memo = create_memo('test note')
    assert memo['visibility'] == 'private'

def test_none_visibility_defaults_to_private():
    memo = create_memo('test note', None)
    assert memo['visibility'] == 'private'

def test_empty_string_visibility_defaults_to_private():
    memo = create_memo('test note', '')
    assert memo['visibility'] == 'private'
