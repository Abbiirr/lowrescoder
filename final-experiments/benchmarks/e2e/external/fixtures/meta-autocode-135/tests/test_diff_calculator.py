import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from diff_calculator import count_changes

# PASS with bug (new_lines are all truly new — len(new_lines) == new lines not in old)

def test_empty_both():
    result = count_changes([], [])
    assert result == {'added': 0, 'removed': 0}

def test_all_new_lines():
    result = count_changes([], ['a', 'b', 'c'])
    assert result['added'] == 3 and result['removed'] == 0

def test_no_new_lines():
    result = count_changes(['a', 'b'], [])
    assert result['added'] == 0 and result['removed'] == 2

def test_disjoint_change():
    result = count_changes(['a', 'b'], ['c', 'd'])
    assert result['added'] == 2 and result['removed'] == 2

# FAIL with bug (unchanged lines counted as additions)

def test_unchanged_lines_not_counted():
    # 'a' is in both — only 'c' is genuinely new
    result = count_changes(['a', 'b'], ['a', 'c'])
    assert result['added'] == 1  # bug: len(['a','c']) = 2

def test_all_unchanged_zero_added():
    result = count_changes(['a', 'b'], ['a', 'b'])
    assert result['added'] == 0  # bug: len(['a','b']) = 2

def test_partial_overlap_added():
    result = count_changes(['x', 'y', 'z'], ['x', 'y', 'w'])
    assert result['added'] == 1  # bug: len(['x','y','w']) = 3
