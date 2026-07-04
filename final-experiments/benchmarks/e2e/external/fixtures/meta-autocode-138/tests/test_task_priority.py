import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from task_priority import get_next_task

# PASS with bug (empty/single task or all same priority)

def test_no_tasks():
    assert get_next_task([]) is None

def test_no_pending_tasks():
    tasks = [{'id': 1, 'status': 'done', 'priority': 1}]
    assert get_next_task(tasks) is None

def test_single_pending():
    tasks = [{'id': 1, 'status': 'pending', 'priority': 5}]
    assert get_next_task(tasks)['id'] == 1

def test_skips_done_tasks():
    tasks = [
        {'id': 1, 'status': 'done', 'priority': 1},
        {'id': 2, 'status': 'pending', 'priority': 3},
    ]
    assert get_next_task(tasks)['id'] == 2

# FAIL with bug (lowest priority_number = highest priority)

def test_lowest_number_first():
    tasks = [
        {'id': 1, 'status': 'pending', 'priority': 3},
        {'id': 2, 'status': 'pending', 'priority': 1},
    ]
    result = get_next_task(tasks)
    assert result['id'] == 2  # bug: returns id=1 (max priority=3)

def test_priority_one_wins():
    tasks = [
        {'id': 10, 'status': 'pending', 'priority': 10},
        {'id': 11, 'status': 'pending', 'priority': 1},
        {'id': 12, 'status': 'pending', 'priority': 5},
    ]
    assert get_next_task(tasks)['id'] == 11  # bug: returns id=10

def test_mixed_status_priority():
    tasks = [
        {'id': 1, 'status': 'done', 'priority': 1},
        {'id': 2, 'status': 'pending', 'priority': 5},
        {'id': 3, 'status': 'pending', 'priority': 2},
    ]
    assert get_next_task(tasks)['id'] == 3  # bug: returns id=2
