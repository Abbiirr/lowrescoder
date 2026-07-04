# TASK-028: Fix Line Range Filter Single-Line Ranges (sharkdp/bat pattern)

## Source
Inspired by sharkdp/bat `--line-range` feature. When the user specifies a
single-line range like `--line-range 5:5`, bat should return exactly that one
line. The bug uses `>=` in the guard, so equal start/end is treated as an
empty range.

## Goal
Fix `src/line_range.py` so `filter_lines()` returns a one-element list when
`start == end`.

## The bug
```python
# BUG: >= treats start==end as empty — single-line ranges return []
if start >= end:
    return []

# Fix: only bail when start > end (invalid range)
if start > end:
    return []
```

## Failing tests (3/7 fail initially)
```
test_single_line_at_start   ← FAILS (1:1 returns [])
test_single_line_in_middle  ← FAILS (5:5 returns [])
test_single_line_at_end     ← FAILS (10:10 returns [])
```
