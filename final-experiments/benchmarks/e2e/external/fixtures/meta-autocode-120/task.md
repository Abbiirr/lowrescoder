# TASK-120: Fix Rate Limiter Off-By-One (louislam/uptime-kuma pattern)

## Source
Inspired by uptime-kuma rate limiting logic. Using `<` instead of `<=` blocks
the last allowed request in a window.

## Goal
Fix `src/rate_limiter.py` so `is_allowed()` permits exactly `max_requests`
requests per window (inclusive).

## The bug
```python
# BUG: < excludes the max_requests-th allowed slot
return bucket['count'] < max_requests

# Fix:
return bucket['count'] <= max_requests
```

## Failing tests (3/7 fail initially)
```
test_exactly_at_limit      ← FAILS (3rd of 3 blocked)
test_max_one_allowed       ← FAILS (1st of 1 blocked)
test_fifth_of_five_allowed ← FAILS (5th of 5 blocked)
```
