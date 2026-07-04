# TASK-191: Fix Left Pad Ignores Pad Character (langflow pattern)

## Source
Inspired by langflow-ai/langflow string formatting utilities. Using `rjust(width)`
without the fill-character argument always pads with spaces, ignoring the
`char` parameter.

## Goal
Fix `src/string_formatter.py` so `left_pad()` passes the `char` argument to
`rjust()`.

## The bug
```python
# BUG: char argument ignored — always pads with space
return s.rjust(width)

# Fix:
return s.rjust(width, char)
```

## Failing tests (3/7 fail initially)
```
test_zero_pad ← FAILS (left_pad('5',3,'0') → bug '  5', should '005')
test_dash_pad ← FAILS (left_pad('hello',8,'-') → bug '   hello')
test_star_pad ← FAILS (left_pad('x',4,'*') → bug '   x')
```
