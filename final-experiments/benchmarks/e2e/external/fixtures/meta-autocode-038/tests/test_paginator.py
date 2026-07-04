import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from paginator import paginate

ITEMS = list(range(1, 11))  # [1, 2, ..., 10]

def test_page1_content():
    result = paginate(ITEMS, 1, 3)
    assert result['items'] == [1, 2, 3]

def test_page2_content():
    result = paginate(ITEMS, 2, 3)
    assert result['items'] == [4, 5, 6]

def test_page_number_in_result():
    result = paginate(ITEMS, 2, 3)
    assert result['page'] == 2

def test_per_page_in_result():
    result = paginate(ITEMS, 1, 3)
    assert result['per_page'] == 3

def test_total_reflects_full_collection():
    # BUG: total = len([1,2,3]) = 3, should be len(ITEMS) = 10
    result = paginate(ITEMS, 1, 3)
    assert result['total'] == 10

def test_total_same_on_page2():
    # BUG: total = 3 (page size), should be 10 (full count)
    result = paginate(ITEMS, 2, 3)
    assert result['total'] == 10

def test_total_correct_on_last_partial_page():
    # BUG: last page has 1 item → total = 1, should be 10
    result = paginate(ITEMS, 4, 3)  # items=[10], partial
    assert result['total'] == 10
