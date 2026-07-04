# TASK-155: Fix HTTP Method Validation Case-Sensitivity (axios pattern)

## Source
Inspired by axios/axios request normalization. Method validation is
case-sensitive so `'get'` and `'post'` are rejected as invalid, even though
HTTP methods are case-insensitive in practice.

## Goal
Fix `src/http_validator.py` so `is_valid_method()` accepts methods regardless
of case.

## The bug
```python
# BUG: 'get' not in {'GET', ...} → False
return method in _ALLOWED_METHODS

# Fix: normalize to uppercase first
return method.upper() in _ALLOWED_METHODS
```

## Failing tests (3/7 fail initially)
```
test_get_lowercase   ← FAILS (False instead of True)
test_post_lowercase  ← FAILS (False instead of True)
test_put_mixed_case  ← FAILS (False instead of True)
```
