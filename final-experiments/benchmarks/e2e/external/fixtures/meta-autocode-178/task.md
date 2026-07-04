# TASK-178: Fix Max Line Length Skips Last Line (bat pattern)

## Source
Inspired by sharkdp/bat line analysis utilities. Using `lines[:-1]` skips the
last element, so `max_line_length()` underreports when the longest line is
the last one.

## Goal
Fix `src/line_analyzer.py` so `max_line_length()` considers all lines
including the last one.

## The bug
```python
# BUG: lines[:-1] drops the last line
return max((len(line) for line in lines[:-1]), default=0)

# Fix:
return max((len(line) for line in lines), default=0)
```

## Failing tests (3/7 fail initially)
```
test_last_is_longest       ← FAILS (bug skips 'longer' → returns 1)
test_two_lines_last_longer ← FAILS (bug skips 'hello world' → returns 2)
test_single_long_last      ← FAILS (bug skips 'looooooong' → returns 1)
```
