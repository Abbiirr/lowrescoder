import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from event_scheduler import get_due_events

# PASS with bug (events scheduled AT current_time: >= and <= both match)

def test_empty_events():
    assert get_due_events([], 100) == []

def test_exact_time_match():
    e = {'id': 1, 'scheduled_at': 100}
    result = get_due_events([e], 100)
    assert e in result  # both >= and <= include equality

def test_all_at_current():
    events = [{'id': i, 'scheduled_at': 50} for i in range(3)]
    result = get_due_events(events, 50)
    assert len(result) == 3

def test_future_event_bug_passes():
    # Bug returns future events; test that checks only exact-time passes
    e1 = {'id': 1, 'scheduled_at': 100}
    e2 = {'id': 2, 'scheduled_at': 200}
    # With bug, both are "due" at t=100 (100>=100 T, 200>=100 T)
    # Check only that e1 is in result — bug agrees
    result = get_due_events([e1, e2], 100)
    assert e1 in result

# FAIL with bug (past events should be due, future should not)

def test_past_event_is_due():
    e = {'id': 1, 'scheduled_at': 50}
    result = get_due_events([e], 100)
    assert e in result  # bug: 50 >= 100 is False, returns []

def test_future_event_not_due():
    e = {'id': 1, 'scheduled_at': 200}
    result = get_due_events([e], 100)
    assert result == []  # bug: 200 >= 100 is True, returns [e]

def test_mixed_events():
    past = {'id': 1, 'scheduled_at': 50}
    future = {'id': 2, 'scheduled_at': 200}
    result = get_due_events([past, future], 100)
    # Only past should be due
    assert result == [past]  # bug: returns [future] only (50>=100 F, 200>=100 T)
