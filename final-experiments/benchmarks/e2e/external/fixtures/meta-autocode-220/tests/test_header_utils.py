import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from header_utils import strip_auth_header

# PASS (no auth header, or exactly canonical 'Authorization' — both agree)

def test_empty():
    assert strip_auth_header({}) == {}

def test_no_auth():
    assert strip_auth_header({'Content-Type': 'json'}) == {'Content-Type': 'json'}

def test_canonical_removed():
    assert strip_auth_header({'Authorization': 'Bearer abc', 'X-ID': '1'}) == {'X-ID': '1'}

def test_canonical_only():
    assert strip_auth_header({'Authorization': 'Basic xyz'}) == {}

# FAIL (non-canonical casing — bug keeps it, fix removes it)

def test_lowercase():
    assert strip_auth_header({'authorization': 'Bearer abc'}) == {}  # bug: keeps it

def test_uppercase():
    assert strip_auth_header({'AUTHORIZATION': 'x'}) == {}  # bug: keeps it

def test_mixed_case_both():
    result = strip_auth_header({'Authorization': 'a', 'authorization': 'b'})
    assert result == {}  # bug: keeps 'authorization'
