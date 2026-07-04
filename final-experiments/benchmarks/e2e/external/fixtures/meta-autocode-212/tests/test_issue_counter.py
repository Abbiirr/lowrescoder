import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from issue_counter import count_open_issues

# PASS (all issues are open — len == open count)

def test_two_open():
    assert count_open_issues([{'state': 'open'}, {'state': 'open'}]) == 2

def test_empty():
    assert count_open_issues([]) == 0

def test_one_open():
    assert count_open_issues([{'state': 'open'}]) == 1

def test_three_open():
    assert count_open_issues([{'state': 'open'}] * 3) == 3

# FAIL (mixed/all-closed — len > open count, bug overcounts)

def test_mixed():
    assert count_open_issues([{'state': 'open'}, {'state': 'closed'}]) == 1  # bug: 2

def test_all_closed_one():
    assert count_open_issues([{'state': 'closed'}]) == 0  # bug: 1

def test_all_closed_two():
    assert count_open_issues([{'state': 'closed'}, {'state': 'closed'}]) == 0  # bug: 2
