import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from line_checker import is_empty_line

# PASS (truly empty or non-whitespace — both bug and fix agree)

def test_empty():
    assert is_empty_line('') is True

def test_word():
    assert is_empty_line('hello') is False

def test_code():
    assert is_empty_line('code here') is False

def test_single_char():
    assert is_empty_line('x') is False

# FAIL (whitespace-only — bug says non-empty, fix says empty)

def test_spaces():
    assert is_empty_line('   ') is True  # bug: False

def test_tab():
    assert is_empty_line('\t') is True  # bug: False

def test_mixed_whitespace():
    assert is_empty_line('  \t  ') is True  # bug: False
