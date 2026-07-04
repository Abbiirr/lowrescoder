import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from config_validator import has_valid_timeout

# PASS (timeout present and positive, or absent — bug and fix agree)

def test_valid_timeout():
    assert has_valid_timeout({'timeout': 5000}) == True

def test_minimal_timeout():
    assert has_valid_timeout({'timeout': 1}) == True

def test_no_timeout():
    assert has_valid_timeout({}) == False

def test_no_timeout_with_other_keys():
    assert has_valid_timeout({'url': 'http://example.com'}) == False

# FAIL (timeout present but zero or negative — bug True, fix False)

def test_zero_timeout():
    assert has_valid_timeout({'timeout': 0}) == False  # bug: True

def test_negative_timeout():
    assert has_valid_timeout({'timeout': -1}) == False  # bug: True

def test_large_negative():
    assert has_valid_timeout({'timeout': -500}) == False  # bug: True
