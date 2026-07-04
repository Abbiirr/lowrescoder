# TASK-139: Fix Config Validator Falsy Check (fastapi/fastapi pattern)

## Source
Inspired by FastAPI dependency injection config validation. Uses `if not value`
(falsy check) instead of `if value is None`, incorrectly treating 0, False,
and [] as missing values.

## Goal
Fix `src/config_validator.py` so `validate_config()` only flags keys where
the value is None or absent, not falsy values like 0, False, or [].

## The bug
```python
# BUG: falsy check — 0, False, [] all treated as missing
if not value:

# Fix: explicit None check
if value is None:
```

## Failing tests (3/7 fail initially)
```
test_zero_is_valid         ← FAILS (port=0 flagged as missing)
test_empty_string_is_missing ← FAILS (enabled=False flagged as missing)
test_empty_list_is_valid   ← FAILS (allowed_hosts=[] flagged as missing)
```
