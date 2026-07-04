import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from paginator import get_page_items

# PASS with bug (empty or out-of-range pages where bug and fix both return [])

def test_empty_items():
    assert get_page_items([], 1, 5) == []

def test_beyond_last_page():
    # 10 items, page_size=5, page=3 → bug: offset=15, []; fix: offset=10, [] — both []
    assert get_page_items(list(range(10)), 3, 5) == []

def test_page2_beyond_5_items():
    # 5 items, page_size=5, page=2 → bug: offset=10, []; fix: offset=5, [] — both []
    assert get_page_items(list(range(5)), 2, 5) == []

def test_large_page():
    assert get_page_items([1, 2, 3], 100, 5) == []

# FAIL with bug (first page and real offsets differ by page_size)

def test_first_page_correct():
    items = list(range(9))
    result = get_page_items(items, 1, 3)
    assert result == [0, 1, 2]  # bug: [3, 4, 5]

def test_single_item_first_page():
    result = get_page_items(['only'], 1, 1)
    assert result == ['only']  # bug: offset=1, returns []

def test_second_page_correct():
    items = list(range(9))
    result = get_page_items(items, 2, 3)
    assert result == [3, 4, 5]  # bug: offset=6, returns [6, 7, 8]
