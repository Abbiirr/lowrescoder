import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from label_manager import add_labels_to_issue

def test_add_to_empty():
    assert add_labels_to_issue([], [1, 2]) == [1, 2]

def test_add_new_unique():
    assert add_labels_to_issue([1], [2, 3]) == [1, 2, 3]

def test_no_new_labels():
    assert add_labels_to_issue([1, 2], []) == [1, 2]

def test_preserve_order():
    assert add_labels_to_issue([3, 1], [2]) == [3, 1, 2]

def test_add_existing_label_no_dup():
    # BUG: [1,2]+[1] = [1,2,1] instead of [1,2]
    assert add_labels_to_issue([1, 2], [1]) == [1, 2]

def test_all_new_are_duplicates():
    # BUG: [1,2,3]+[1,2] = [1,2,3,1,2] instead of [1,2,3]
    assert add_labels_to_issue([1, 2, 3], [1, 2]) == [1, 2, 3]

def test_mixed_new_and_existing():
    # BUG: [1]+[1,2] = [1,1,2] instead of [1,2]
    assert add_labels_to_issue([1], [1, 2]) == [1, 2]
