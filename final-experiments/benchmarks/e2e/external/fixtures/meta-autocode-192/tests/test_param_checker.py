import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from param_checker import is_valid_param_name

# PASS (valid non-keyword identifiers and clearly invalid names)

def test_normal_param():
    assert is_valid_param_name('user_id') == True

def test_simple_name():
    assert is_valid_param_name('limit') == True

def test_starts_with_digit():
    assert is_valid_param_name('123invalid') == False

def test_empty():
    assert is_valid_param_name('') == False

# FAIL (Python keywords — bug returns True, fix returns False)

def test_class_keyword():
    assert is_valid_param_name('class') == False  # bug: True

def test_return_keyword():
    assert is_valid_param_name('return') == False  # bug: True

def test_for_keyword():
    assert is_valid_param_name('for') == False  # bug: True
