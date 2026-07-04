# TASK-182: Fix Range Check Excludes Maximum Value (langflow pattern)

## Source
Inspired by langflow-ai/langflow parameter validation. Using `<` instead of
`<=` for the upper-bound check makes the range exclusive at the max, so
`is_in_range(10, 0, 10)` incorrectly returns False.

## Goal
Fix `src/param_validator.py` so `is_in_range()` treats the range as fully
inclusive on both ends.

## The bug
```python
# BUG: < excludes max_val
return min_val <= value < max_val

# Fix:
return min_val <= value <= max_val
```

## Failing tests (3/7 fail initially)
```
test_at_maximum       ← FAILS (is_in_range(10,0,10) → bug False, should True)
test_single_point_range ← FAILS (is_in_range(5,5,5) → bug False, should True)
test_at_large_max     ← FAILS (is_in_range(100,0,100) → bug False, should True)
```
