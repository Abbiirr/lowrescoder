# TASK-135: Fix Diff Calculator Added Count (jesseduffield/lazygit pattern)

## Source
Inspired by lazygit diff statistics. Counts all new_lines as additions
instead of only lines not present in old_lines.

## Goal
Fix `src/diff_calculator.py` so `count_changes()` counts only genuinely
new lines (in new but not in old) as additions.

## The bug
```python
# BUG: counts ALL new lines, including unchanged ones
added = len(new_lines)

# Fix: set difference
added = len(set(new_lines) - set(old_lines))
```

## Failing tests (3/7 fail initially)
```
test_unchanged_lines_not_counted ← FAILS (added=2 instead of 1)
test_all_unchanged_zero_added    ← FAILS (added=2 instead of 0)
test_partial_overlap_added       ← FAILS (added=3 instead of 1)
```
