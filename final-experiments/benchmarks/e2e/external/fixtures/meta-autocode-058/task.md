# TASK-058: Fix Integer Range Bound Validation (fastapi/fastapi pattern)

## Source
Inspired by FastAPI path/query parameter constraints (`ge`, `le`). When a
parameter has `ge=0, le=100`, values outside that range must raise a
`ValueError`. The bug ignores bounds and always returns the value.

## Goal
Fix `src/range_validator.py` so `validate_int_range()` raises `ValueError`
when `value < ge` or `value > le`.

## The bug
```python
# BUG: no range check
return value

# Fix: enforce bounds
if ge is not None and value < ge:
    raise ValueError(f"{value} is less than minimum {ge}")
if le is not None and value > le:
    raise ValueError(f"{value} exceeds maximum {le}")
return value
```

## Failing tests (3/7 fail initially)
```
test_below_ge_raises             ← FAILS (-1 with ge=0 returns -1, should raise)
test_above_le_raises             ← FAILS (101 with le=100 returns 101, should raise)
test_below_lower_bound_both_set  ← FAILS (-5 with ge=0,le=100 returns -5, should raise)
```
