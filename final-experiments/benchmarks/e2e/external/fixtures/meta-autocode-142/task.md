# TASK-142: Fix String Truncator Max Length (sharkdp/bat pattern)

## Source
Inspired by bat output formatting. Truncates to max_length then appends
ellipsis, producing a result longer than max_length.

## Goal
Fix `src/string_truncator.py` so the result never exceeds `max_length`
characters (ellipsis included).

## The bug
```python
# BUG: slice max_length then add ellipsis → len = max_length + 3
return text[:max_length] + ellipsis

# Fix: reserve space for ellipsis
return text[:max_length - len(ellipsis)] + ellipsis
```

## Failing tests (3/7 fail initially)
```
test_result_length_not_exceeded ← FAILS (len = 11 > 8)
test_exact_max_length           ← FAILS (len = 8 > 5)
test_truncation_fits            ← FAILS (len = 13 > 10)
```
