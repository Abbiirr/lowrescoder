# TASK-114: Fix Event Deduplicator Key Includes Resource ID (go-gitea/gitea pattern)

## Source
Inspired by go-gitea/gitea event deduplication. The dedup key must be
(type, resource_id) tuple, not just type alone.

## Goal
Fix `src/event_deduplicator.py` so `deduplicate_events()` uses both `type`
and `resource_id` as the composite dedup key.

## The bug
```python
# BUG: key is type only
key = event.get('type')

# Fix:
key = (event.get('type'), event.get('resource_id'))
```

## Failing tests (3/7 fail initially)
```
test_same_type_different_resource_kept ← FAILS (1 != 2; wrong dedup)
test_same_type_multiple_resources      ← FAILS (1 != 3)
test_mixed_dedup                       ← FAILS (1 != 2)
```
