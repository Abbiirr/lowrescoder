import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from color_validator import is_valid_label_color

# --- PASS with bug (valid hex or empty — both agree) ---

def test_valid_red():
    assert is_valid_label_color('#ff0000') is True

def test_valid_blue():
    assert is_valid_label_color('#0000ff') is True

def test_empty_string_rejected():
    assert is_valid_label_color('') is False

def test_valid_mixed_case_hex():
    assert is_valid_label_color('#A1B2C3') is True

# --- FAIL with bug (non-hex non-empty: bug True, fix False) ---

def test_no_hash_prefix_rejected():
    assert is_valid_label_color('ff0000') is False

def test_invalid_hex_chars_rejected():
    assert is_valid_label_color('#gggggg') is False

def test_short_hex_rejected():
    assert is_valid_label_color('#fff') is False
