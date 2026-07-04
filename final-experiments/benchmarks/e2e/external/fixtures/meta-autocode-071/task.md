# TASK-071: Fix HTTP Error Response Detection (axios/axios pattern)

## Source
Inspired by axios/axios response interceptors. axios treats any non-2xx
response as an error, including 4xx client errors. The bug only checks for
server errors (>= 500), silently passing 4xx responses.

## Goal
Fix `src/error_detector.py` so `is_error_response()` returns `True` for any
status code outside the 200-299 range.

## The bug
```python
# BUG: only catches 5xx
return status_code >= 500

# Fix: catch all non-2xx
return not (200 <= status_code < 300)
```

## Failing tests (3/7 fail initially)
```
test_400_is_error ← FAILS (400 returns False — should be True)
test_404_is_error ← FAILS (404 returns False — should be True)
test_403_is_error ← FAILS (403 returns False — should be True)
```
