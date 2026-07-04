import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from list_rotator import rotate_right

# PASS with bug (edge cases where left == right rotation)

def test_empty_list():
    assert rotate_right([]) == []

def test_single_element():
    assert rotate_right([42]) == [42]

def test_two_elements():
    # Right: [a,b] → [b,a]; Left: [a,b] → [b,a] — same!
    assert rotate_right(['a', 'b']) == ['b', 'a']

def test_alternating_pattern():
    # [1,2,1,2]: left=[2,1,2,1], right=[2,1,2,1] — same!
    assert rotate_right([1, 2, 1, 2]) == [2, 1, 2, 1]

# FAIL with bug (right rotation puts last element first; left puts second element first)

def test_three_elements():
    # Right: [1,2,3] → [3,1,2]; Left: [2,3,1]
    assert rotate_right([1, 2, 3]) == [3, 1, 2]

def test_four_elements():
    # Right: [1,2,3,4] → [4,1,2,3]; Left: [2,3,4,1]
    assert rotate_right([1, 2, 3, 4]) == [4, 1, 2, 3]

def test_last_becomes_first():
    result = rotate_right(['x', 'y', 'z'])
    assert result[0] == 'z'  # bug: result[0] == 'y'
