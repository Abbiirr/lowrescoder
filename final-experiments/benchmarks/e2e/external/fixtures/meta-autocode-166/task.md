# TASK-166: Fix Value Clamping — Swapped Bounds (uptime-kuma pattern)

## Source
Inspired by louislam/uptime-kuma metric normalization. The clamp function
returns the wrong bound: when below min it returns max_val, and when above max
it returns min_val.

## Goal
Fix `src/value_clamp.py` so `clamp()` returns the correct bound.

## The bug
```python
# BUG: bounds swapped
if value < min_val:
    return max_val   # should return min_val
if value > max_val:
    return min_val   # should return max_val

# Fix:
if value < min_val:
    return min_val
if value > max_val:
    return max_val
```

## Failing tests (3/7 fail initially)
```
test_below_min    ← FAILS (10 instead of 0)
test_above_max    ← FAILS (0 instead of 10)
test_far_below_min ← FAILS (8 instead of 2)
```
