import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from query_param import parse_query_int

# PASS (valid integer string — both bug and fix return int(value))

def test_five():
    assert parse_query_int('5') == 5

def test_zero():
    assert parse_query_int('0') == 0

def test_hundred():
    assert parse_query_int('100') == 100

def test_forty_two():
    assert parse_query_int('42') == 42

# FAIL (None value — bug raises TypeError, fix returns default)

def test_none_default_zero():
    assert parse_query_int(None) == 0  # bug: TypeError

def test_none_default_ten():
    assert parse_query_int(None, 10) == 10  # bug: TypeError

def test_none_default_99():
    assert parse_query_int(None, 99) == 99  # bug: TypeError
