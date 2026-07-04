# TASK-068: Fix Per-Request Timeout Override (axios/axios pattern)

## Source
Inspired by axios/axios request config merging. When making a request, a
per-request `timeout` should override the axios instance's default timeout.
The bug always returns the instance-level timeout, ignoring the request-level
override.

## Goal
Fix `src/timeout_merger.py` so `resolve_request_timeout()` returns
`request_timeout` when it is not `None`, else `instance_timeout`.

## The bug
```python
# BUG: always returns instance timeout
return instance_timeout

# Fix: prefer request_timeout when provided
return request_timeout if request_timeout is not None else instance_timeout
```

## Failing tests (3/7 fail initially)
```
test_request_timeout_overrides_instance  ← FAILS (1000ms ignored, returns 5000ms)
test_request_timeout_longer_than_instance ← FAILS (30000ms ignored, returns 1000ms)
test_request_timeout_zero_overrides      ← FAILS (0ms timeout ignored, returns 5000ms)
```
