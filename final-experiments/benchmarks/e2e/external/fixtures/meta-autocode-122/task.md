# TASK-122: Fix Syntax Highlighter Range Boundary (sharkdp/bat pattern)

## Source
Inspired by sharkdp/bat line highlighting. Highlight ranges use exclusive
end (`<`) when they should be inclusive (`<=`), so the last line of each
range is never highlighted.

## Goal
Fix `src/syntax_highlighter.py` so `get_highlight_lines()` includes the
`range_end` line (inclusive boundary).

## The bug
```python
# BUG: exclusive end — range_end line is never highlighted
if range_start <= line < range_end:

# Fix: inclusive end
if range_start <= line <= range_end:
```

## Failing tests (3/7 fail initially)
```
test_range_end_inclusive      ← FAILS (line 5 excluded from range (3,5))
test_single_line_range        ← FAILS (range (4,4) returns empty set)
test_view_end_line_highlighted ← FAILS (line 10 excluded from range (9,10))
```
