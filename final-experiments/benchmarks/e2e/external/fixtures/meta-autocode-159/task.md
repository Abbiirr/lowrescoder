# TASK-159: Fix Date Range Overlap Detection (memos pattern)

## Source
Inspired by usememos/memos date filtering. The overlap check uses "range1
contains range2" logic, missing partial overlaps and the case where range2
contains range1.

## Goal
Fix `src/date_range.py` so `ranges_overlap()` correctly detects all overlapping
date ranges.

## The bug
```python
# BUG: only True when range1 contains range2
return start1 <= start2 and end1 >= end2

# Fix: standard overlap — neither ends before the other starts
return start1 <= end2 and start2 <= end1
```

## Failing tests (3/7 fail initially)
```
test_partial_overlap_left    ← FAILS (False instead of True)
test_partial_overlap_right   ← FAILS (False instead of True)
test_range2_contains_range1  ← FAILS (False instead of True)
```
