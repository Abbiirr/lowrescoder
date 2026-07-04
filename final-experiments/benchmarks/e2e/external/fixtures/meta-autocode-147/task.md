# TASK-147: Fix HTTP Retry Status Check (axios/axios pattern)

## Source
Inspired by axios retry logic. Retries on HTTP 200 (success) instead of
5xx (server errors), causing retries after success and no retries on failure.

## Goal
Fix `src/http_retry.py` so `should_retry()` retries only on 5xx status codes.

## The bug
```python
# BUG: retries on success (200)
return status_code == 200

# Fix: retry on server errors
return 500 <= status_code < 600
```

## Failing tests (3/7 fail initially)
```
test_500_should_retry    ← FAILS (False instead of True)
test_503_should_retry    ← FAILS (False instead of True)
test_200_should_not_retry ← FAILS (True instead of False)
```
