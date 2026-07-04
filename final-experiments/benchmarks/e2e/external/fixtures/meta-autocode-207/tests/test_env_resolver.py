import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from env_resolver import get_env_var

# PASS (key exists — default irrelevant, bug and fix agree)

def test_key_present():
    assert get_env_var({'PORT': '3000'}, 'PORT', '8080') == '3000'

def test_host_present():
    assert get_env_var({'HOST': 'localhost'}, 'HOST', '0.0.0.0') == 'localhost'

def test_no_default_needed():
    assert get_env_var({'PORT': '3000'}, 'PORT') == '3000'

def test_multiple_keys():
    assert get_env_var({'A': 1, 'B': 2}, 'A', 99) == 1

# FAIL (key missing — bug returns None, fix returns default)

def test_missing_with_default():
    assert get_env_var({}, 'PORT', '8080') == '8080'  # bug: None

def test_missing_in_partial_config():
    assert get_env_var({'HOST': 'localhost'}, 'PORT', '3000') == '3000'  # bug: None

def test_missing_bool_default():
    assert get_env_var({}, 'DEBUG', False) == False  # bug: None
