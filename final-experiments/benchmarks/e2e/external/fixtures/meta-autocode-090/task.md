# TASK-090: Fix Uptime Percentage Calculator (louislam/uptime-kuma pattern)

## Source
Inspired by louislam/uptime-kuma uptime ratio calculation. The bug uses total
check count as the numerator instead of the count of 'up' checks.

## Goal
Fix `src/uptime_calculator.py` so `calculate_uptime_percentage()` counts only
checks where `status == 'up'`.

## The bug
```python
# BUG: counts total instead of 'up' checks
up_count = len(checks)

# Fix: count only 'up' checks
up_count = sum(1 for c in checks if c.get('status') == 'up')
```

## Failing tests (3/7 fail initially)
```
test_half_up_half_down  ← FAILS (100.0 != 50.0)
test_one_up_three_down  ← FAILS (100.0 != 25.0)
test_all_down_is_zero   ← FAILS (100.0 != 0.0)
```
