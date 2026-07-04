# TASK-177: Fix Uptime Percentage Case-Sensitive Status Check (uptime-kuma pattern)

## Source
Inspired by louislam/uptime-kuma monitor status tracking. Status checks
arriving as 'up' or 'Up' are not counted because the comparison is
case-sensitive.

## Goal
Fix `src/uptime_calculator.py` so `uptime_percentage()` counts any
capitalisation of 'up' as an UP status.

## The bug
```python
# BUG: case-sensitive — 'up', 'Up' not counted as UP
up_count = sum(1 for c in checks if c == 'UP')

# Fix:
up_count = sum(1 for c in checks if c.upper() == 'UP')
```

## Failing tests (3/7 fail initially)
```
test_lowercase_all_up ← FAILS ('up' not counted — returns 0.0)
test_mixed_case_up    ← FAILS ('UP','up' → only 1 counted → 50% not 100%)
test_title_case       ← FAILS ('Up' not counted — returns 0.0)
```
