# TASK-246: Fix get_rate_limit() Wrong Key 'rate' vs 'limit' (fastapi pattern)

## Source
Inspired by fastapi/fastapi rate limiting settings. Config uses 'limit', not 'rate'.

## Goal
Fix `src/rate_limit.py` so `get_rate_limit()` reads the correct `'limit'` key.

## The bug
```python
# BUG: wrong key
return settings.get('rate', default)

# Fix:
return settings.get('limit', default)
```

## Failing tests (3/7 fail initially)
```
test_limit_50  ← FAILS ({'limit': 50} → bug:100, correct:50)
test_limit_200 ← FAILS ({'limit': 200} → bug:100, correct:200)
test_limit_500 ← FAILS ({'limit': 500} → bug:100, correct:500)
```
