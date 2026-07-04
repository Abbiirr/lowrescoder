# TASK-205: Fix Page Count Truncates Instead of Rounding Up (bat pattern)

## Source
Inspired by sharkdp/bat pager output calculation. Integer division drops the
remainder, so `page_count(1, 10)` returns 0 (no pages) instead of 1.

## Goal
Fix `src/paginator.py` so `page_count()` rounds up to include any partial
last page.

## The bug
```python
# BUG: truncates — partial page dropped
return total_items // page_size

# Fix:
return math.ceil(total_items / page_size)
```

## Failing tests (3/7 fail initially)
```
test_remainder   ← FAILS (10//3=3, ceil=4)
test_half_page   ← FAILS (7//2=3, ceil=4)
test_single_item ← FAILS (1//10=0, ceil=1)
```
