# TASK-160: Fix Palindrome Case-Sensitivity (fastapi pattern)

## Source
Inspired by fastapi/fastapi string validation utilities. Case-sensitive
comparison treats 'Racecar' as non-palindrome because 'R' != 'r'.

## Goal
Fix `src/string_utils.py` so `is_palindrome()` compares case-insensitively.

## The bug
```python
# BUG: 'Racecar' → 'Racecar' != 'racecaR' → False
return cleaned == cleaned[::-1]

# Fix: normalize case first
return cleaned.lower() == cleaned.lower()[::-1]
```

## Failing tests (3/7 fail initially)
```
test_mixed_case_racecar ← FAILS (False instead of True)
test_mixed_case_madam   ← FAILS (False instead of True)
test_mixed_case_level   ← FAILS (False instead of True)
```
