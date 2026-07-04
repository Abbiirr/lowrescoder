# TASK-021: Fix Terminal Display Width Tab Expansion (sharkdp/bat pattern)

## Source
Inspired by sharkdp/bat terminal display width calculation.
bat must calculate the display width of source lines to align line numbers and
highlights. The bug: `display_width()` uses `len(text)`, which counts `\t` as
width 1. Tabs must advance to the next tab stop.

## Goal
Fix `src/display_width.py` so `display_width()` expands tabs correctly.

## The bug
```python
# BUG: counts \t as 1 character
return len(text)

# Fix: expand tabs to tab stops first
return len(text.expandtabs(tab_width))
```

## Failing tests (3/7 fail initially)
```
test_single_tab_at_start  ← FAILS (got 6, expected 9)
test_tab_in_middle        ← FAILS (got 5, expected 6)
test_multiple_tabs        ← FAILS (got 2, expected 8)
```
