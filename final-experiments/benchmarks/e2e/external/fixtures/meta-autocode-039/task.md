# TASK-039: Fix Numeric Input Validator Max Inclusive (langflow-ai/langflow pattern)

## Source
Inspired by langflow-ai/langflow component input validation. When a component
input has `max_val=100`, a user providing exactly 100 should be valid. The bug
uses `>= max_val`, which rejects the boundary value as if it exceeded the max.

## Goal
Fix `src/input_validator.py` so `validate_numeric_input()` treats `max_val` as
inclusive (raises only when `value > max_val`).

## The bug
```python
# BUG: >= max_val rejects the boundary value itself
if max_val is not None and value >= max_val:
    raise ValueError(...)

# Fix: strict > allows the boundary value
if max_val is not None and value > max_val:
    raise ValueError(...)
```

## Failing tests (3/7 fail initially)
```
test_max_boundary_valid    ← FAILS (value=10, max=10 → ValueError)
test_max_exactly_100       ← FAILS (value=100, max=100 → ValueError)
test_max_equals_value_small ← FAILS (value=5, max=5 → ValueError)
```
