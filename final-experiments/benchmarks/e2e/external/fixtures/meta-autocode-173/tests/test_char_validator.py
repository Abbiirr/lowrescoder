import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from char_validator import is_printable_ascii

# PASS (all chars in printable range 32-126 — bug and fix agree)

def test_empty_string():
    assert is_printable_ascii('') == True

def test_letters():
    assert is_printable_ascii('Hello') == True

def test_alphanumeric_space():
    assert is_printable_ascii('abc 123') == True

def test_punctuation():
    assert is_printable_ascii('!@#$') == True

# FAIL (control chars < 32 — bug returns True, fix returns False)

def test_tab():
    assert is_printable_ascii('\t') == False  # bug: True (ord 9 < 127)

def test_newline():
    assert is_printable_ascii('\n') == False  # bug: True (ord 10 < 127)

def test_null():
    assert is_printable_ascii('\x00') == False  # bug: True (ord 0 < 127)
