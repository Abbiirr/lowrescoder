# TASK-024: Fix HTTP Monitor Status Code Range Check (louislam/uptime-kuma pattern)

## Source
Inspired by louislam/uptime-kuma HTTP monitor. Uptime-kuma considers a
monitor "up" for any 2xx HTTP response code. The bug checks only for 200,
so 201 Created, 204 No Content, and other 2xx codes are falsely reported
as "down".

## Goal
Fix `src/heartbeat.py` so `compute_status()` treats any HTTP 2xx response
as "up" when no `expected_codes` override is given.

## The bug
```python
# BUG: only checks for 200 exactly
return response_code == 200

# Fix: accept full 2xx range
return 200 <= response_code < 300
```

## Failing tests (3/7 fail initially)
```
test_201_created_is_up    ← FAILS (201 treated as down)
test_204_no_content_is_up ← FAILS (204 treated as down)
test_299_edge_of_2xx_is_up ← FAILS (299 treated as down)
```
