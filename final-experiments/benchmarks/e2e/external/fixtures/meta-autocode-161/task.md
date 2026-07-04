# TASK-161: Fix Mode Finder — min vs max (bat pattern)

## Source
Inspired by sharkdp/bat statistics utilities. `find_mode()` uses `min()` to
find the item with the lowest frequency instead of `max()` for the highest.

## Goal
Fix `src/stats_utils.py` so `find_mode()` returns the most frequent item.

## The bug
```python
# BUG: min → least frequent
return min(counts, key=lambda k: counts[k])

# Fix: max → most frequent
return max(counts, key=lambda k: counts[k])
```

## Failing tests (3/7 fail initially)
```
test_one_winner    ← FAILS (1 instead of 2)
test_clear_leader  ← FAILS (4 instead of 3)
test_tail_heavy    ← FAILS (5 instead of 6)
```
