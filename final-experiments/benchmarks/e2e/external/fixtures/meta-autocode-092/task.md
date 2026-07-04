# TASK-092: Fix Session Expiry TTL Unit (louislam/uptime-kuma pattern)

## Source
Inspired by louislam/uptime-kuma session management. The TTL parameter is in
minutes but the bug compares it directly against elapsed seconds.

## Goal
Fix `src/session_expiry.py` so `is_session_expired()` converts `ttl_minutes`
to seconds before comparing.

## The bug
```python
# BUG: compares seconds against minutes directly
return (current_time - created_at) > ttl_minutes

# Fix: convert to seconds
return (current_time - created_at) > ttl_minutes * 60
```

## Failing tests (3/7 fail initially)
```
test_fifty_seconds_not_expired       ← FAILS (True != False; 50>30 but 50<1800)
test_twenty_nine_minutes_not_expired ← FAILS (True != False; 1740>30 but 1740<1800)
test_exactly_thirty_minutes          ← FAILS (True != False; 1800>30 but 1800=1800)
```
