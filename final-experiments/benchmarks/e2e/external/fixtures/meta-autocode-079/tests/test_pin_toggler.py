import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from pin_toggler import toggle_pin

# --- PASS with bug (pinned=False → True is correct in both cases) ---

def test_unpin_to_pinned():
    memo = {'pinned': False, 'content': 'hello'}
    result = toggle_pin(memo)
    assert result['pinned'] is True

def test_no_pinned_key_becomes_pinned():
    memo = {'content': 'hello'}
    result = toggle_pin(memo)
    assert result['pinned'] is True

def test_content_preserved_after_pin():
    memo = {'pinned': False, 'content': 'my note'}
    toggle_pin(memo)
    assert memo['content'] == 'my note'

def test_returns_memo_object():
    memo = {'pinned': False}
    assert toggle_pin(memo) is memo

# --- FAIL with bug (pinned=True → bug keeps True, fix sets False) ---

def test_pinned_memo_gets_unpinned():
    memo = {'pinned': True}
    result = toggle_pin(memo)
    assert result['pinned'] is False

def test_double_toggle_returns_to_original():
    memo = {'pinned': False}
    toggle_pin(memo)
    toggle_pin(memo)
    assert memo['pinned'] is False

def test_pinned_memo_unpin_preserves_content():
    memo = {'pinned': True, 'content': 'secret note'}
    result = toggle_pin(memo)
    assert result['pinned'] is False
    assert result['content'] == 'secret note'
