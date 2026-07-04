import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from line_formatter import format_line_number

# --- PASS with bug (files with 1000-9999 lines — width 4 is correct) ---

def test_thousand_line_file_first_line():
    assert format_line_number(1, 1000) == '   1'

def test_thousand_line_file_last_line():
    assert format_line_number(1000, 1000) == '1000'

def test_large_file_small_number():
    assert format_line_number(5, 5000) == '   5'

def test_four_digit_total():
    assert format_line_number(999, 9999) == ' 999'

# --- FAIL with bug (< 1000 lines: fix uses smaller width, bug always 4) ---

def test_small_file_width_2():
    # 50 lines → width should be 2; fix: ' 1', bug: '   1'
    assert format_line_number(1, 50) == ' 1'

def test_single_digit_total():
    # 9 lines → width 1; fix: '3', bug: '   3'
    assert format_line_number(3, 9) == '3'

def test_two_digit_total():
    # 99 lines → width 2; fix: '42', bug: '  42'
    assert format_line_number(42, 99) == '42'
