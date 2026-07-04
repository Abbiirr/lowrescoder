# TASK-193: Fix Timeout Validator Accepts Zero/Negative Values (axios pattern)

## Source
Inspired by axios/axios request configuration validation. Checking only
`'timeout' in config` accepts invalid values like 0 or negative numbers as
valid timeouts.

## Goal
Fix `src/config_validator.py` so `has_valid_timeout()` requires the timeout
to be a positive number (> 0).

## The bug
```python
# BUG: only checks key existence
return 'timeout' in config

# Fix:
return 'timeout' in config and config['timeout'] > 0
```

## Failing tests (3/7 fail initially)
```
test_zero_timeout    ← FAILS (0 is not a valid timeout — bug True)
test_negative_timeout ← FAILS (-1 not valid — bug True)
test_large_negative  ← FAILS (-500 not valid — bug True)
```
