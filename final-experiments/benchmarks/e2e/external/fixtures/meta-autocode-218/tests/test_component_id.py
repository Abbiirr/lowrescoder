import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from component_id import is_valid_component_id

# PASS (purely alphanumeric — isalnum() agrees with correct logic)

def test_lowercase_alpha():
    assert is_valid_component_id('abc123') is True

def test_uppercase():
    assert is_valid_component_id('ABC') is True

def test_digits_only():
    assert is_valid_component_id('123') is True

def test_empty():
    assert is_valid_component_id('') is False

# FAIL (contains underscore — bug rejects, fix accepts)

def test_with_underscore():
    assert is_valid_component_id('my_component') is True  # bug: False

def test_underscore_number():
    assert is_valid_component_id('node_1') is True  # bug: False

def test_multi_underscore():
    assert is_valid_component_id('chat_model_v2') is True  # bug: False
