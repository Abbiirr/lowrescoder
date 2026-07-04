# TASK-163: Fix Missing Return True in Uniqueness Check (langflow pattern)

## Source
Inspired by langflow-ai/langflow node input validation. The loop correctly
returns False on duplicate, but falls off the end of the function (returns
None) instead of returning True when all elements are unique.

## Goal
Fix `src/collection_utils.py` so `all_unique()` returns True when no
duplicates are found.

## The bug
```python
# BUG: missing 'return True' after the loop
seen.add(item)
# (function returns None implicitly)

# Fix:
seen.add(item)
return True
```

## Failing tests (3/7 fail initially)
```
test_empty_list   ← FAILS (None instead of True)
test_single_item  ← FAILS (None instead of True)
test_all_different ← FAILS (None instead of True)
```
