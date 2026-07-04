# TASK-060: Fix Flow Execution Timeout Default (langflow-ai/langflow pattern)

## Source
Inspired by langflow-ai/langflow flow runner timeout handling. Non-positive
timeouts (0 or negative) should fall back to a DEFAULT_TIMEOUT of 30 seconds.
The bug returns raw timeout values unchanged.

## Goal
Fix `src/timeout_resolver.py` so `resolve_timeout()` returns
`DEFAULT_TIMEOUT` (30) when `timeout <= 0`.

## The bug
```python
# BUG: returns raw value — no default substitution
return timeout

# Fix: default on non-positive
return timeout if timeout > 0 else DEFAULT_TIMEOUT
```

## Failing tests (3/7 fail initially)
```
test_zero_uses_default          ← FAILS (0 returns 0, expected 30)
test_negative_one_uses_default  ← FAILS (-1 returns -1, expected 30)
test_large_negative_uses_default ← FAILS (-100 returns -100, expected 30)
```
