import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from build_mode import is_dev_mode

# PASS (no 'mode' or both env and mode agree)

def test_empty():
    assert is_dev_mode({}) is False

def test_production_mode():
    assert is_dev_mode({'mode': 'production'}) is False

def test_both_development():
    assert is_dev_mode({'env': 'development', 'mode': 'development'}) is True

def test_both_production():
    assert is_dev_mode({'env': 'production', 'mode': 'production'}) is False

# FAIL (mode is 'development' but env is not — bug returns False)

def test_mode_only():
    assert is_dev_mode({'mode': 'development'}) is True  # bug: False

def test_mode_dev_env_prod():
    assert is_dev_mode({'mode': 'development', 'env': 'production'}) is True  # bug: False

def test_mode_dev_with_port():
    assert is_dev_mode({'mode': 'development', 'port': 5173}) is True  # bug: False
