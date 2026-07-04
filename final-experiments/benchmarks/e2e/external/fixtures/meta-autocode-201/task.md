# TASK-201: Fix Pagination Limit Max Threshold Too High (fastapi pattern)

## Source
Inspired by fastapi/fastapi query parameter validation. The limit upper bound
is 1000 instead of 100, allowing oversized page requests.

## Goal
Fix `src/pagination.py` so `validate_limit()` rejects values > 100.

## The bug
```python
# BUG: max 1000 instead of 100
return isinstance(limit, int) and 1 <= limit <= 1000

# Fix:
return isinstance(limit, int) and 1 <= limit <= 100
```

## Failing tests (3/7 fail initially)
```
test_just_over_max ← FAILS (101 accepted — bug True)
test_large_value   ← FAILS (500 accepted — bug True)
test_at_bug_max    ← FAILS (1000 accepted — bug True)
```
