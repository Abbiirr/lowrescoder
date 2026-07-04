import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from heartbeat_validator import validate_heartbeat_interval

# --- PASS with bug (both return same result) ---

def test_valid_60_seconds():
    assert validate_heartbeat_interval(60) is True

def test_valid_20_seconds():
    # Boundary: exactly 20 is valid; both > 0 and >= 20 agree
    assert validate_heartbeat_interval(20) is True

def test_invalid_zero():
    assert validate_heartbeat_interval(0) is False

def test_invalid_negative():
    assert validate_heartbeat_interval(-5) is False

# --- FAIL with bug (1-19 seconds: bug True, fix False) ---

def test_too_small_1_second():
    assert validate_heartbeat_interval(1) is False

def test_too_small_10_seconds():
    assert validate_heartbeat_interval(10) is False

def test_too_small_19_seconds():
    assert validate_heartbeat_interval(19) is False
