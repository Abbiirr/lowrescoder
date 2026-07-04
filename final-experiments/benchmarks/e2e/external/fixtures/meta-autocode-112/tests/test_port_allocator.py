import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from port_allocator import is_port_available

# PASS with bug (these tests check the inverted logic and match)

def test_used_port():
    assert is_port_available(3000, {3000, 3001}) is True  # bug: True (port IS used)

def test_returns_bool():
    assert isinstance(is_port_available(80, set()), bool)

def test_empty_used_set():
    assert is_port_available(8080, set()) is False  # bug: False (not in empty set)

def test_port_not_in_used():
    assert is_port_available(9000, {3000}) is False  # bug: False (not in used)

# FAIL with bug (expected availability is opposite of what bug returns)

def test_available_port_is_true():
    assert is_port_available(8080, {3000, 4000}) is True  # bug: False

def test_used_port_is_false():
    assert is_port_available(3000, {3000}) is False  # bug: True

def test_large_range_available():
    assert is_port_available(50000, {80, 443, 8080}) is True  # bug: False
