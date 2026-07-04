import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from line_normalizer import normalize_line_endings

# --- PASS with bug (Unix or CRLF — both handle these) ---

def test_unix_unchanged():
    assert normalize_line_endings('hello\nworld') == 'hello\nworld'

def test_crlf_normalized():
    assert normalize_line_endings('a\r\nb') == 'a\nb'

def test_empty_string():
    assert normalize_line_endings('') == ''

def test_no_line_endings():
    assert normalize_line_endings('hello') == 'hello'

# --- FAIL with bug (standalone \r not replaced) ---

def test_cr_only():
    assert normalize_line_endings('a\rb') == 'a\nb'

def test_mixed_crlf_and_cr():
    assert normalize_line_endings('a\r\nb\rc') == 'a\nb\nc'

def test_multiple_cr():
    assert normalize_line_endings('x\ry\rz') == 'x\ny\nz'
