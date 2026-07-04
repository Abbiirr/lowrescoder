# TASK-162: Fix Digit Sum for Negative Numbers (lazygit pattern)

## Source
Inspired by jesseduffield/lazygit number formatting. `str(negative)` includes
`'-'` so `int('-')` raises ValueError when iterating over characters.

## Goal
Fix `src/number_utils.py` so `digit_sum()` handles negative numbers by
ignoring the sign.

## The bug
```python
# BUG: '-' in str(-5) = '-5' → int('-') raises ValueError
return sum(int(d) for d in str(n))

# Fix: use abs() to strip sign
return sum(int(d) for d in str(abs(n)))
```

## Failing tests (3/7 fail initially)
```
test_negative_single    ← FAILS (ValueError)
test_negative_multi     ← FAILS (ValueError)
test_negative_with_zero ← FAILS (ValueError)
```
