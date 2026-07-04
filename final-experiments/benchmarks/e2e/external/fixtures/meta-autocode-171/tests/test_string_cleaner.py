import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from string_cleaner import strip_leading_zeros

# PASS (not all zeros — both return same non-empty string)

def test_no_leading_zeros():
    assert strip_leading_zeros('123') == '123'

def test_padded_number():
    assert strip_leading_zeros('007') == '7'  # both strip to '7'

def test_single_nonzero():
    assert strip_leading_zeros('1') == '1'

def test_internal_zero():
    assert strip_leading_zeros('0100') == '100'  # strips leading 0 → '100'

# FAIL (all zeros — bug returns '', fix returns '0')

def test_single_zero():
    assert strip_leading_zeros('0') == '0'  # bug: '' (lstrip removes the only char)

def test_double_zero():
    assert strip_leading_zeros('00') == '0'  # bug: ''

def test_triple_zero():
    assert strip_leading_zeros('000') == '0'  # bug: ''
