import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from header_checker import has_header

# --- PASS with bug (exact case match or truly missing) ---

def test_exact_case_match():
    assert has_header({'Content-Type': 'application/json'}, 'Content-Type') is True

def test_missing_header():
    assert has_header({'Content-Type': 'application/json'}, 'Authorization') is False

def test_empty_headers():
    assert has_header({}, 'Content-Type') is False

def test_exact_case_custom_header():
    assert has_header({'X-Request-Id': 'abc123'}, 'X-Request-Id') is True

# --- FAIL with bug (case mismatch) ---

def test_lowercase_lookup_on_title_case():
    assert has_header({'Content-Type': 'application/json'}, 'content-type') is True

def test_uppercase_stored_lowercase_lookup():
    assert has_header({'AUTHORIZATION': 'Bearer token'}, 'authorization') is True

def test_title_case_lookup_on_lowercase_stored():
    assert has_header({'content-type': 'text/html'}, 'Content-Type') is True
