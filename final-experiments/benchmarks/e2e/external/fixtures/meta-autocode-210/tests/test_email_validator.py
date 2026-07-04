import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from email_validator import is_valid_email

# PASS (clearly valid or clearly invalid — both bug and fix agree)

def test_valid_email():
    assert is_valid_email('user@example.com') is True

def test_minimal_valid():
    assert is_valid_email('a@b') is True

def test_no_at_sign():
    assert is_valid_email('noemail') is False

def test_empty_string():
    assert is_valid_email('') is False

# FAIL (pass the '@' check but are structurally invalid)

def test_missing_local_part():
    assert is_valid_email('@example.com') is False  # bug: True

def test_missing_domain():
    assert is_valid_email('user@') is False  # bug: True

def test_double_at():
    assert is_valid_email('user@@example.com') is False  # bug: True
