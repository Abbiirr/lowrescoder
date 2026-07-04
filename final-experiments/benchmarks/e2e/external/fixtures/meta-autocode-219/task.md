# TASK-219: Fix is_body_too_large Uses >= Instead of > (fastapi pattern)

## Source
Inspired by fastapi/fastapi request body size limits. Using >= rejects
bodies at exactly the allowed maximum, which should be permitted.

## Goal
Fix `src/body_size.py` so `is_body_too_large()` returns True only when
the content length strictly exceeds max_size.

## The bug
```python
# BUG: >= rejects exact-limit bodies
return len(content) >= max_size

# Fix:
return len(content) > max_size
```

## Failing tests (3/7 fail initially)
```
test_exactly_at_limit_10 ← FAILS (len 10, max 10 → bug:True, correct:False)
test_exactly_at_limit_5  ← FAILS (len 5, max 5 → bug:True, correct:False)
test_exactly_at_limit_3  ← FAILS (len 3, max 3 → bug:True, correct:False)
```
