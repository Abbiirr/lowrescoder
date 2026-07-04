import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from scope_checker import has_required_scopes

# --- PASS with bug (full match or no match — both agree) ---

def test_all_required_present():
    assert has_required_scopes(['read', 'write', 'admin'], ['read', 'write']) is True

def test_no_overlap_returns_false():
    assert has_required_scopes(['read'], ['write', 'admin']) is False

def test_empty_token_required_non_empty():
    assert has_required_scopes([], ['read']) is False

def test_exact_match():
    assert has_required_scopes(['read', 'write'], ['read', 'write']) is True

# --- FAIL with bug (partial overlap: bug True because any intersection, fix False) ---

def test_partial_match_insufficient():
    # Token has 'read' but not 'write' — bug sees overlap with required=['read','write']
    assert has_required_scopes(['read'], ['read', 'write']) is False

def test_one_of_two_scopes_missing():
    assert has_required_scopes(['admin'], ['read', 'admin']) is False

def test_empty_required_returns_true():
    # No scopes required → always allowed; bug: empty intersection → False
    assert has_required_scopes(['read', 'write'], []) is True
