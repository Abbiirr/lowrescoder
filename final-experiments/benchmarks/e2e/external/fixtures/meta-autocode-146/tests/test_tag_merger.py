import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from tag_merger import merge_tag_sets

# PASS with bug (intersection == union for identical sets, or only shared items checked)

def test_empty_both():
    assert merge_tag_sets(set(), set()) == set()

def test_identical_sets():
    s = {'python', 'web', 'api'}
    assert merge_tag_sets(s, s) == s  # intersection of identical == union

def test_shared_element_present():
    # bug: {'x'}; fix: {'x','y','z'} — both contain 'x'
    result = merge_tag_sets({'x', 'y'}, {'x', 'z'})
    assert 'x' in result

def test_returns_a_set():
    result = merge_tag_sets({'a'}, {'a', 'b'})
    assert isinstance(result, set)

# FAIL with bug (union must include unique elements from each set)

def test_disjoint_sets():
    # bug: {} (no intersection); fix: {'a','b'}
    result = merge_tag_sets({'a'}, {'b'})
    assert result == {'a', 'b'}

def test_unique_elements_from_a_included():
    result = merge_tag_sets({'alpha', 'beta'}, {'beta', 'gamma'})
    assert 'alpha' in result  # bug: only {'beta'} — 'alpha' missing

def test_all_unique_elements():
    result = merge_tag_sets({'p', 'q'}, {'q', 'r'})
    assert result == {'p', 'q', 'r'}  # bug: {'q'}
