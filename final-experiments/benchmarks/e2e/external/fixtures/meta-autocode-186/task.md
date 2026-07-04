# TASK-186: Fix Response Threshold Check Uses <= Instead of < (uptime-kuma pattern)

## Source
Inspired by louislam/uptime-kuma response time validation. Using `<=` accepts
a response time exactly at the threshold as "OK", but the spec requires
strictly less than the threshold.

## Goal
Fix `src/threshold_check.py` so `is_response_ok()` uses strict less-than.

## The bug
```python
# BUG: <= accepts exact-threshold as OK
return response_ms <= max_ms

# Fix:
return response_ms < max_ms
```

## Failing tests (3/7 fail initially)
```
test_exactly_at_threshold ← FAILS (500 <= 500 → True, should be False)
test_equal_small          ← FAILS (100 <= 100 → True, should be False)
test_equal_medium         ← FAILS (200 <= 200 → True, should be False)
```
