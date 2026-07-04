import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from server_config import get_port

# PASS (no 'port' key — bug and fix both return the default)

def test_empty_config():
    assert get_port({}) == 3000

def test_unrelated_keys():
    assert get_port({'host': 'localhost'}) == 3000

def test_debug_flag():
    assert get_port({'debug': True}) == 3000

def test_custom_default():
    assert get_port({}, default=8080) == 8080

# FAIL ('port' key present — bug ignores it and returns default, fix returns value)

def test_port_8080():
    assert get_port({'port': 8080}) == 8080  # bug: 3000

def test_port_5173():
    assert get_port({'port': 5173}) == 5173  # bug: 3000

def test_port_with_host():
    assert get_port({'port': 4000, 'host': '0.0.0.0'}) == 4000  # bug: 3000
