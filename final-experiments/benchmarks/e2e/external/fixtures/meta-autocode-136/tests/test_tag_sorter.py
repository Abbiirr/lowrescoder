import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from tag_sorter import sort_tags

# PASS with bug (name sort is correct; count sort of 1 element)

def test_empty_tags():
    assert sort_tags([]) == []

def test_sort_by_name():
    tags = [{'name': 'zig'}, {'name': 'apple'}, {'name': 'mango'}]
    result = sort_tags(tags, by='name')
    assert [t['name'] for t in result] == ['apple', 'mango', 'zig']

def test_single_tag_count():
    tags = [{'name': 'a', 'count': 5}]
    result = sort_tags(tags, by='count')
    assert result == tags  # single element — asc and desc same

def test_sort_by_name_default():
    tags = [{'name': 'b'}, {'name': 'a'}]
    result = sort_tags(tags)
    assert result[0]['name'] == 'a'

# FAIL with bug (count sort must be descending)

def test_sort_by_count_descending():
    tags = [{'name': 'a', 'count': 1}, {'name': 'b', 'count': 5}, {'name': 'c', 'count': 3}]
    result = sort_tags(tags, by='count')
    # Correct: [5, 3, 1]; bug: [1, 3, 5]
    assert [t['count'] for t in result] == [5, 3, 1]

def test_highest_count_first():
    tags = [{'name': 'x', 'count': 10}, {'name': 'y', 'count': 100}]
    result = sort_tags(tags, by='count')
    assert result[0]['count'] == 100  # bug: result[0]['count'] == 10

def test_count_sort_three_descending():
    tags = [{'name': 'p', 'count': 7}, {'name': 'q', 'count': 2}, {'name': 'r', 'count': 9}]
    result = sort_tags(tags, by='count')
    assert result[0]['name'] == 'r'  # bug: 'q' (lowest count first)
