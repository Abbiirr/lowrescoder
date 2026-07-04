# TASK-081: Fix Line Numbering Start Offset (sharkdp/bat pattern)

## Source
Inspired by sharkdp/bat line number rendering. The `number_lines()` function
must respect the `start` parameter instead of always using 0-based indexing.

## Goal
Fix `src/line_numberer.py` so `number_lines(lines, start=1)` uses `start`
as the first line number.

## The bug
```python
# BUG: always starts at 0
for i, line in enumerate(lines):
    result.append((i, line))

# Fix: use start parameter
for i, line in enumerate(lines, start=start):
    result.append((i, line))
```

## Failing tests (3/7 fail initially)
```
test_default_start_is_1   ← FAILS (returns 0, expected 1)
test_start_param_respected ← FAILS (returns 0, 1, expected 5, 6)
test_zero_start_allowed   ← FAILS (partially; first element ok, second wrong)
```
