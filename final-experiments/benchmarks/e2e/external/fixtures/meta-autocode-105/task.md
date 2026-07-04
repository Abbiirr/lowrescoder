# TASK-105: Fix Watch Counter Field Update (go-gitea/gitea pattern)

## Source
Inspired by go-gitea/gitea repository watch tracking. The function must update
`repo['watch_count']` in addition to returning the count.

## Goal
Fix `src/watch_counter.py` so `update_watch_count()` stores the new count
in `repo['watch_count']` before returning.

## The bug
```python
# BUG: returns count but doesn't store it in repo
return len(watchers)

# Fix:
repo['watch_count'] = len(watchers)
return repo['watch_count']
```

## Failing tests (3/7 fail initially)
```
test_watch_count_field_updated      ← FAILS (repo['watch_count'] stays 0)
test_unwatch_decrements_field       ← FAILS (repo['watch_count'] stays 1)
test_watch_count_matches_watchers   ← FAILS (repo['watch_count'] stays 0)
```
