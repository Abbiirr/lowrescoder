# TASK-210: Fix is_valid_email Accepts Malformed Addresses (fastapi pattern)

## Source
Inspired by fastapi/fastapi email dependency validation. A naive '@' check
accepts malformed addresses that would fail real validation.

## Goal
Fix `src/email_validator.py` so `is_valid_email()` requires non-empty local
and domain parts with exactly one '@'.

## The bug
```python
# BUG: only checks '@' presence
return '@' in email

# Fix:
parts = email.split('@')
return len(parts) == 2 and all(parts)
```

## Failing tests (3/7 fail initially)
```
test_missing_local_part  ← FAILS ('@example.com' has '@', bug returns True)
test_missing_domain      ← FAILS ('user@' has '@', bug returns True)
test_double_at           ← FAILS ('user@@example.com' has '@', bug returns True)
```
