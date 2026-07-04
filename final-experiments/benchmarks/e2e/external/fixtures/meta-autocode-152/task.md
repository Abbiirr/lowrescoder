# TASK-152: Fix Event Log Recent-N Slicing (gitea pattern)

## Source
Inspired by go-gitea/gitea activity feed. Returns the first N events instead
of the last N (most recent), using `[:n]` instead of `[-n:]`.

## Goal
Fix `src/event_log.py` so `get_recent_events()` returns the last N items from
the chronologically ordered list.

## The bug
```python
# BUG: returns oldest N events
return events[:n]

# Fix: returns most recent N events
return events[-n:]
```

## Failing tests (3/7 fail initially)
```
test_last_three_of_five ← FAILS ([1,2,3] instead of [3,4,5])
test_last_two_of_four   ← FAILS ([10,20] instead of [30,40])
test_last_one           ← FAILS ([1] instead of [5])
```
