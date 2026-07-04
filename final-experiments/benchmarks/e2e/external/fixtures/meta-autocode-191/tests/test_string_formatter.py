import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from string_formatter import left_pad

# PASS (char is space — bug and fix agree)

def test_space_pad():
    assert left_pad('hello', 10, ' ') == '     hello'

def test_single_char_space():
    assert left_pad('a', 3, ' ') == '  a'

def test_already_at_width():
    assert left_pad('hello', 5, ' ') == 'hello'

def test_wider_string():
    assert left_pad('hello', 3, ' ') == 'hello'

# FAIL (non-space char — bug pads with space, fix uses char)

def test_zero_pad():
    assert left_pad('5', 3, '0') == '005'  # bug: '  5'

def test_dash_pad():
    assert left_pad('hello', 8, '-') == '---hello'  # bug: '   hello'

def test_star_pad():
    assert left_pad('x', 4, '*') == '***x'  # bug: '   x'
