# TASK-204: Fix Stale Alert Check Uses > Instead of >= (uptime-kuma pattern)

## Source
Inspired by louislam/uptime-kuma alert staleness detection. Using `>` means
an alert that has aged exactly to the threshold is not flagged as stale.

## Goal
Fix `src/alert_checker.py` so `is_stale_alert()` flags alerts at or beyond
the threshold.

## The bug
```python
# BUG: > excludes exact threshold
return age_seconds > max_age

# Fix:
return age_seconds >= max_age
```

## Failing tests (3/7 fail initially)
```
test_exactly_at_max ← FAILS (300 > 300 → False, should True)
test_equal_small    ← FAILS (60 > 60 → False)
test_equal_large    ← FAILS (3600 > 3600 → False)
```
