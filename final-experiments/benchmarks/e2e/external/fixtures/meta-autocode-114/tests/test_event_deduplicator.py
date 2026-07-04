import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from event_deduplicator import deduplicate_events

# PASS with bug (same type AND resource — both deduplicate the same)

def test_empty_input():
    assert deduplicate_events([]) == []

def test_no_duplicates_unchanged():
    events = [{'type': 'push', 'resource_id': 1}, {'type': 'pull', 'resource_id': 2}]
    assert len(deduplicate_events(events)) == 2

def test_same_type_same_resource_deduped():
    events = [{'type': 'push', 'resource_id': 1}, {'type': 'push', 'resource_id': 1}]
    assert len(deduplicate_events(events)) == 1

def test_first_event_kept():
    events = [{'type': 'push', 'resource_id': 1, 'seq': 1}, {'type': 'push', 'resource_id': 1, 'seq': 2}]
    assert deduplicate_events(events)[0]['seq'] == 1

# FAIL with bug (same type, different resource should NOT be deduped)

def test_same_type_different_resource_kept():
    events = [{'type': 'push', 'resource_id': 1}, {'type': 'push', 'resource_id': 2}]
    result = deduplicate_events(events)
    assert len(result) == 2  # bug: 1 (type-only dedup)

def test_same_type_multiple_resources():
    events = [{'type': 'update', 'resource_id': i} for i in range(3)]
    assert len(deduplicate_events(events)) == 3  # bug: 1

def test_mixed_dedup():
    events = [
        {'type': 'push', 'resource_id': 1},
        {'type': 'push', 'resource_id': 2},  # different resource, same type
        {'type': 'push', 'resource_id': 1},  # true dup
    ]
    assert len(deduplicate_events(events)) == 2  # bug: 1
