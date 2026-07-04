# TASK-097: Fix Retry Backoff Addition vs Multiplication (axios/axios pattern)

## Source
Inspired by axios/axios retry delay calculation. Exponential backoff is
`base_delay * 2^attempt`, not `base_delay + 2^attempt`.

## Goal
Fix `src/retry_calculator.py` so `get_retry_delay()` multiplies.

## The bug
```python
# BUG: addition
delay = base_delay + (2 ** attempt)

# Fix: multiplication
delay = base_delay * (2 ** attempt)
```

## Failing tests (3/7 fail initially)
```
test_attempt_zero_base_delay ← FAILS (2.0 != 1.0)
test_attempt_one             ← FAILS (3.0 != 2.0)
test_attempt_two             ← FAILS (5.0 != 4.0)
```
