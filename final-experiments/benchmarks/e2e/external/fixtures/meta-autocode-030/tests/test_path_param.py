import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
import pytest
from path_param import parse_path_param

def test_positive_int():
    assert parse_path_param('42', 'int') == 42

def test_zero():
    assert parse_path_param('0', 'int') == 0

def test_large_positive():
    assert parse_path_param('1000', 'int') == 1000

def test_string_passthrough():
    assert parse_path_param('hello', 'str') == 'hello'

def test_negative_int():
    # BUG: '-1'.isdigit() is False → raises ValueError instead of returning -1
    assert parse_path_param('-1', 'int') == -1

def test_negative_large():
    # BUG: '-100'.isdigit() is False → raises ValueError
    assert parse_path_param('-100', 'int') == -100

def test_negative_id():
    # BUG: '-42'.isdigit() is False → raises ValueError
    assert parse_path_param('-42', 'int') == -42
