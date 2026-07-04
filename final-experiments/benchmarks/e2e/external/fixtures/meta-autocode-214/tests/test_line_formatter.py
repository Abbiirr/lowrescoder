import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from line_formatter import format_line_number

# PASS (number fills or overflows width — str(n) == rjust result)

def test_exact_width():
    assert format_line_number(1234, 4) == '1234'

def test_overflow():
    assert format_line_number(123456, 4) == '123456'

def test_exact_four_digits():
    assert format_line_number(1000, 4) == '1000'

def test_two_digit_width_two():
    assert format_line_number(12, 2) == '12'

# FAIL (number shorter than width — bug gives no padding, fix pads)

def test_single_digit_width_four():
    assert format_line_number(1, 4) == '   1'  # bug: '1'

def test_two_digit_width_five():
    assert format_line_number(42, 5) == '   42'  # bug: '42'

def test_three_digit_width_six():
    assert format_line_number(100, 6) == '   100'  # bug: '100'
