# TASK-063: Fix Rate Limiter Boundary Check (fastapi/fastapi pattern)

## Source
Inspired by FastAPI middleware rate limiting. A request that makes the count
equal to the limit (e.g. 100th request with limit=100) should be blocked. The
bug uses strict greater-than (`>`) instead of greater-than-or-equal (`>=`).

## Goal
Fix `src/rate_limiter.py` so `is_rate_limited()` returns `True` when
`request_count >= limit`.

## The bug
```python
# BUG: strict > allows exactly limit requests
return request_count > limit

# Fix: inclusive >=
return request_count >= limit
```

## Failing tests (3/7 fail initially)
```
test_exactly_at_limit  ← FAILS (100 with limit=100 returns False, should be True)
test_at_limit_small    ← FAILS (10 with limit=10 returns False, should be True)
test_at_limit_one      ← FAILS (1 with limit=1 returns False, should be True)
```
