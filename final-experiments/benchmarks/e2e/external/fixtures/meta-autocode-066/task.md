# TASK-066: Fix HTTP 2xx Status Check (louislam/uptime-kuma pattern)

## Source
Inspired by louislam/uptime-kuma monitor health checks. A successful response
is any 2xx status code, not only 200. The bug checks for exactly 200, causing
201 Created, 204 No Content, etc. to be treated as failures.

## Goal
Fix `src/status_checker.py` so `is_status_ok()` returns `True` for any
status code in the range 200-299 inclusive.

## The bug
```python
# BUG: only accepts 200
return status_code == 200

# Fix: accept all 2xx
return 200 <= status_code < 300
```

## Failing tests (3/7 fail initially)
```
test_201_created_is_ok   ← FAILS (201 returns False, should be True)
test_204_no_content_is_ok ← FAILS (204 returns False, should be True)
test_202_accepted_is_ok   ← FAILS (202 returns False, should be True)
```
