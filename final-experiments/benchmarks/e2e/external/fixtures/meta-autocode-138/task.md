# TASK-138: Fix Task Priority Selection (langflow-ai/langflow pattern)

## Source
Inspired by langflow task queue ordering. Returns the task with the
highest priority_number (lowest priority) instead of the lowest number
(highest priority).

## Goal
Fix `src/task_priority.py` so `get_next_task()` returns the pending task
with the lowest priority number.

## The bug
```python
# BUG: max returns highest number = lowest priority
return max(pending, key=lambda t: t.get('priority', 0))

# Fix:
return min(pending, key=lambda t: t.get('priority', 0))
```

## Failing tests (3/7 fail initially)
```
test_lowest_number_first  ← FAILS (id=1 returned instead of id=2)
test_priority_one_wins    ← FAILS (id=10 returned instead of id=11)
test_mixed_status_priority ← FAILS (id=2 returned instead of id=3)
```
