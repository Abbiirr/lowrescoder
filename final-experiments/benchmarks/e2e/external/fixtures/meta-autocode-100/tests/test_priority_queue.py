import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from priority_queue import get_highest_priority

# PASS with bug (single item or equal priorities)

def test_empty_returns_none():
    assert get_highest_priority([]) is None

def test_single_item_returned():
    items = [{'name': 'a', 'priority': 5}]
    assert get_highest_priority(items)['name'] == 'a'

def test_returns_dict():
    items = [{'name': 'x', 'priority': 1}]
    assert isinstance(get_highest_priority(items), dict)

def test_equal_priorities():
    items = [{'name': 'a', 'priority': 3}, {'name': 'b', 'priority': 3}]
    result = get_highest_priority(items)
    assert result['priority'] == 3

# FAIL with bug (min instead of max)

def test_highest_priority_selected():
    items = [{'name': 'low', 'priority': 1}, {'name': 'high', 'priority': 10}]
    assert get_highest_priority(items)['name'] == 'high'  # bug: 'low'

def test_three_items_max():
    items = [{'name': 'a', 'priority': 2}, {'name': 'b', 'priority': 8}, {'name': 'c', 'priority': 5}]
    assert get_highest_priority(items)['name'] == 'b'  # bug: 'a'

def test_priority_order():
    items = [{'id': 1, 'priority': 100}, {'id': 2, 'priority': 1}]
    assert get_highest_priority(items)['id'] == 1  # bug: 2
