# TASK-171: Fix Leading Zero Strip Edge Case (vite pattern)

## Source
Inspired by vitejs/vite asset version handling. `lstrip('0')` returns an empty
string for all-zero inputs like `'0'` or `'000'`, but the result should always
keep at least one digit.

## Goal
Fix `src/string_cleaner.py` so `strip_leading_zeros()` returns `'0'` for
all-zero inputs.

## The bug
```python
# BUG: returns '' for all-zero strings
return s.lstrip('0')

# Fix: fallback to '0' if result is empty
return s.lstrip('0') or '0'
```

## Failing tests (3/7 fail initially)
```
test_single_zero  ← FAILS ('' instead of '0')
test_double_zero  ← FAILS ('' instead of '0')
test_triple_zero  ← FAILS ('' instead of '0')
```
