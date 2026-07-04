import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from bool_coercer import coerce_to_bool

def test_true_bool():
    assert coerce_to_bool(True) is True

def test_false_bool():
    assert coerce_to_bool(False) is False

def test_one_is_true():
    assert coerce_to_bool(1) is True

def test_string_true():
    assert coerce_to_bool("true") is True  # bool("true") = True, passes

def test_string_false():
    # BUG: bool("false") = True (non-empty string), should be False
    assert coerce_to_bool("false") is False

def test_string_false_capitalized():
    # BUG: bool("False") = True, should be False
    assert coerce_to_bool("False") is False

def test_string_zero():
    # BUG: bool("0") = True (non-empty string), should be False
    assert coerce_to_bool("0") is False
