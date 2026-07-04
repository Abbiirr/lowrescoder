# TASK-222: Fix format_duration Calculates Total Minutes Not Remainder (uptime-kuma pattern)

## Source
Inspired by louislam/uptime-kuma uptime duration display. Using total
seconds // 60 gives total minutes rather than the within-hour remainder.

## Goal
Fix `src/duration_formatter.py` so `format_duration()` shows the correct
minutes remainder within each hour.

## The bug
```python
# BUG: total minutes, not remainder
m = seconds // 60

# Fix:
m = (seconds % 3600) // 60
```

## Failing tests (3/7 fail initially)
```
test_exactly_one_hour    ← FAILS (3600 → bug:'1h 60m 0s', correct:'1h 0m 0s')
test_two_hours           ← FAILS (7200 → bug:'2h 120m 0s', correct:'2h 0m 0s')
test_one_hour_one_minute ← FAILS (3660 → bug:'1h 61m 0s', correct:'1h 1m 0s')
```
