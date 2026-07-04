import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from memo_tagger import find_memos_by_tag

# PASS (bug and fix agree)

def test_empty_memos():
    assert find_memos_by_tag([], 'python') == []

def test_exact_match():
    memo = {'id': 1, 'tags': ['python', 'code']}
    result = find_memos_by_tag([memo], 'python')
    assert result == [memo]  # same case → both find it

def test_tag_absent():
    memo = {'id': 1, 'tags': ['java']}
    assert find_memos_by_tag([memo], 'python') == []  # not present → both []

def test_multiple_memos_exact():
    m1 = {'id': 1, 'tags': ['python']}
    m2 = {'id': 2, 'tags': ['java']}
    result = find_memos_by_tag([m1, m2], 'python')
    assert result == [m1]  # exact match only m1

# FAIL (case-insensitive required)

def test_uppercase_tag_query():
    memo = {'id': 1, 'tags': ['python']}
    result = find_memos_by_tag([memo], 'Python')
    assert result == [memo]  # bug: 'Python' not in ['python'] → []

def test_uppercase_stored_tag():
    memo = {'id': 1, 'tags': ['PYTHON']}
    result = find_memos_by_tag([memo], 'python')
    assert result == [memo]  # bug: 'python' not in ['PYTHON'] → []

def test_mixed_case():
    memo = {'id': 1, 'tags': ['PyThOn']}
    result = find_memos_by_tag([memo], 'python')
    assert result == [memo]  # bug: case mismatch → []
