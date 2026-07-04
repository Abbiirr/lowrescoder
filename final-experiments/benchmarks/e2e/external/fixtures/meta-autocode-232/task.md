# TASK-232: Fix is_empty_line Misses Whitespace-Only Lines (bat pattern)

## Source
Inspired by sharkdp/bat blank-line detection. Only comparing to '' misses
lines containing just spaces or tabs.

## Goal
Fix `src/line_checker.py` so `is_empty_line()` returns True for any line
containing only whitespace.

## The bug
```python
# BUG: exact empty check
return line == ''

# Fix:
return not line.strip()
```

## Failing tests (3/7 fail initially)
```
test_spaces           ← FAILS ('   ' → bug:False, correct:True)
test_tab              ← FAILS ('\t' → bug:False, correct:True)
test_mixed_whitespace ← FAILS ('  \t  ' → bug:False, correct:True)
```
