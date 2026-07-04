import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from error_classifier import is_timeout_error

# PASS (no TIMEOUT code, or both type and code are TIMEOUT)

def test_empty():
    assert is_timeout_error({}) is False

def test_network_error():
    assert is_timeout_error({'code': 'NETWORK_ERROR'}) is False

def test_both_timeout():
    assert is_timeout_error({'code': 'TIMEOUT', 'type': 'TIMEOUT'}) is True

def test_non_timeout():
    assert is_timeout_error({'code': 'AUTH_ERROR', 'type': 'AUTH_ERROR'}) is False

# FAIL (code is TIMEOUT but type is missing or different — bug returns False)

def test_code_timeout_only():
    assert is_timeout_error({'code': 'TIMEOUT'}) is True  # bug: False

def test_code_timeout_with_message():
    assert is_timeout_error({'code': 'TIMEOUT', 'message': 'timed out'}) is True  # bug: False

def test_code_timeout_type_error():
    assert is_timeout_error({'code': 'TIMEOUT', 'type': 'error'}) is True  # bug: False
