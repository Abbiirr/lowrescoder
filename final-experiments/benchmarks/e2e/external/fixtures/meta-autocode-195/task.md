# TASK-195: Fix Health Threshold Wrong Value (uptime-kuma pattern)

## Source
Inspired by louislam/uptime-kuma health status classification. The threshold
is set to 99 instead of 99.5, so monitors with 99.0–99.4% uptime are
incorrectly marked as healthy.

## Goal
Fix `src/health_checker.py` so `is_healthy()` uses 99.5 as the threshold.

## The bug
```python
# BUG: threshold 99 instead of 99.5
return uptime_percent >= 99

# Fix:
return uptime_percent >= 99.5
```

## Failing tests (3/7 fail initially)
```
test_exactly_99 ← FAILS (99.0 should fail threshold — bug True)
test_99_2       ← FAILS (99.2 < 99.5 — bug True)
test_99_4       ← FAILS (99.4 < 99.5 — bug True)
```
