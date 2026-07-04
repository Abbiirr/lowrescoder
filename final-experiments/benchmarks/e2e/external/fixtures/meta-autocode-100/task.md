# TASK-100: Fix Priority Queue Min vs Max (langflow-ai/langflow pattern)

## Source
Inspired by langflow-ai/langflow component priority ordering. The highest
priority item should be selected with `max()`, not `min()`.

## Goal
Fix `src/priority_queue.py` so `get_highest_priority()` returns the item
with the maximum priority value.

## The bug
```python
# BUG: min returns lowest priority
return min(items, key=lambda x: x.get('priority', 0))

# Fix:
return max(items, key=lambda x: x.get('priority', 0))
```

## Failing tests (3/7 fail initially)
```
test_highest_priority_selected ← FAILS ('low' != 'high')
test_three_items_max           ← FAILS ('a' != 'b')
test_priority_order            ← FAILS (2 != 1)
```
