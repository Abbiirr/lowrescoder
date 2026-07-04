import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from page_calculator import get_page_count

# PASS with bug (evenly divisible)

def test_zero_items():
    assert get_page_count(0, 10) == 0

def test_exactly_one_page():
    assert get_page_count(10, 10) == 1

def test_exactly_two_pages():
    assert get_page_count(20, 10) == 2

def test_large_even():
    assert get_page_count(100, 25) == 4

# FAIL with bug (remainder needs extra page)

def test_one_extra_item():
    assert get_page_count(11, 10) == 2  # bug: 1

def test_partial_first_page():
    assert get_page_count(5, 10) == 1  # bug: 0

def test_nine_items_three_per_page():
    assert get_page_count(9, 4) == 3  # bug: 2
