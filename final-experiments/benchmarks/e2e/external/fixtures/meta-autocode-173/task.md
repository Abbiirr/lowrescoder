# TASK-173: Fix ASCII Printable Check Missing Lower Bound (langflow pattern)

## Source
Inspired by langflow-ai/langflow input validation utilities. The check only
enforces an upper bound (`< 127`) but not a lower bound, so control characters
(tab, newline, null) are incorrectly accepted as "printable".

## Goal
Fix `src/char_validator.py` so `is_printable_ascii()` rejects any character
with `ord(c) < 32` (control characters).

## The bug
```python
# BUG: no lower-bound check — control chars (0-31) pass
return all(ord(c) < 127 for c in text)

# Fix:
return all(32 <= ord(c) <= 126 for c in text)
```

## Failing tests (3/7 fail initially)
```
test_tab      ← FAILS (bug returns True for '\t')
test_newline  ← FAILS (bug returns True for '\n')
test_null     ← FAILS (bug returns True for '\x00')
```
