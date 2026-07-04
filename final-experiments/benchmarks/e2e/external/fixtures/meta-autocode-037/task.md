# TASK-037: Fix Retry Policy for 5xx Status Codes (axios/axios pattern)

## Source
Inspired by axios/axios retry adapter. When a server returns a 5xx status,
clients should retry the request. The bug only retries on exactly 500 (Internal
Server Error), missing 502 (Bad Gateway), 503 (Service Unavailable), and 504
(Gateway Timeout) which are equally retryable.

## Goal
Fix `src/retry_policy.py` so `should_retry()` returns True for all 5xx codes.

## The bug
```python
# BUG: only retries on exactly 500
return status_code == 500

# Fix: retry on any 5xx
return 500 <= status_code < 600
```

## Failing tests (3/7 fail initially)
```
test_retry_on_502  ← FAILS (502 returns False)
test_retry_on_503  ← FAILS (503 returns False)
test_retry_on_504  ← FAILS (504 returns False)
```
