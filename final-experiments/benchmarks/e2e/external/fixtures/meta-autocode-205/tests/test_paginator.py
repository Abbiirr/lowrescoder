import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from paginator import page_count

# PASS (items divide evenly — bug and fix agree)

def test_divisible():
    assert page_count(9, 3) == 3

def test_zero_items():
    assert page_count(0, 10) == 0

def test_two_pages():
    assert page_count(10, 5) == 2

def test_ten_pages():
    assert page_count(100, 10) == 10

# FAIL (non-even division — bug truncates, fix rounds up)

def test_remainder():
    assert page_count(10, 3) == 4  # bug: 3 (10//3=3, drops remainder 1)

def test_half_page():
    assert page_count(7, 2) == 4  # bug: 3 (7//2=3)

def test_single_item():
    assert page_count(1, 10) == 1  # bug: 0 (1//10=0)
