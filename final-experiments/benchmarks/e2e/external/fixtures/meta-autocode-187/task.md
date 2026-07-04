# TASK-187: Fix Line Counter Phantom Extra Line (bat pattern)

## Source
Inspired by sharkdp/bat line counting. Using `text.count('\\n') + 1` adds a
phantom line for empty strings and for text that ends with a newline.

## Goal
Fix `src/line_counter.py` so `count_lines()` returns the correct count using
`splitlines()`.

## The bug
```python
# BUG: extra line for empty string and trailing newline
return text.count('\n') + 1

# Fix:
return len(text.splitlines())
```

## Failing tests (3/7 fail initially)
```
test_empty_string          ← FAILS ('' → bug 1, should 0)
test_trailing_newline      ← FAILS ('hello\\n' → bug 2, should 1)
test_two_lines_trailing_newline ← FAILS ('a\\nb\\n' → bug 3, should 2)
```
