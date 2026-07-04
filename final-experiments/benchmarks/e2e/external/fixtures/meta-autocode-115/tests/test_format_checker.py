import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from format_checker import is_valid_email

# PASS with bug (2-char TLD)

def test_two_char_tld():
    assert is_valid_email('user@example.uk') is True

def test_invalid_no_at():
    assert is_valid_email('notanemail') is False

def test_invalid_no_tld():
    assert is_valid_email('user@domain') is False

def test_empty_is_invalid():
    assert is_valid_email('') is False

# FAIL with bug (TLD longer than 2 chars rejected)

def test_com_tld():
    assert is_valid_email('user@example.com') is True  # bug: False (3 chars)

def test_org_tld():
    assert is_valid_email('hello@world.org') is True  # bug: False

def test_io_and_long_tld():
    assert is_valid_email('dev@company.info') is True  # bug: False (4 chars)
