# TASK-054: Fix Heartbeat Interval Minimum Validation (louislam/uptime-kuma pattern)

## Source
Inspired by louislam/uptime-kuma heartbeat monitor configuration. To prevent
excessive polling, intervals must be at least 20 seconds. The bug only checks
that the interval is positive (> 0), allowing dangerously short values.

## Goal
Fix `src/heartbeat_validator.py` so `validate_heartbeat_interval()` returns
`True` only when `interval_seconds >= 20`.

## The bug
```python
# BUG: only checks > 0 — allows 1-19 second intervals
return interval_seconds > 0

# Fix: enforce minimum 20 seconds
return interval_seconds >= 20
```

## Failing tests (3/7 fail initially)
```
test_too_small_1_second   ← FAILS (1 returns True, should be False)
test_too_small_10_seconds ← FAILS (10 returns True, should be False)
test_too_small_19_seconds ← FAILS (19 returns True, should be False)
```
