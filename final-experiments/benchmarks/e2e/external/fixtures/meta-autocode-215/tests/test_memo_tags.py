import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from memo_tags import get_memo_tags

# PASS (no tags present — both bug and fix return [])

def test_empty_memo():
    assert get_memo_tags({}) == []

def test_no_tags_key():
    assert get_memo_tags({'content': 'hello'}) == []

def test_empty_tags_list():
    assert get_memo_tags({'tags': []}) == []

def test_empty_tags_with_content():
    assert get_memo_tags({'content': 'test', 'tags': []}) == []

# FAIL (memo has tags — bug reads wrong key, fix reads correct key)

def test_single_tag():
    assert get_memo_tags({'tags': ['python']}) == ['python']  # bug: []

def test_two_tags():
    assert get_memo_tags({'tags': ['a', 'b']}) == ['a', 'b']  # bug: []

def test_three_tags():
    assert get_memo_tags({'tags': ['x', 'y', 'z']}) == ['x', 'y', 'z']  # bug: []
