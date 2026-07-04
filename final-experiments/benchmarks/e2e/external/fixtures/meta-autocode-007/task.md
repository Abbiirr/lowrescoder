# TASK-007: Fix Pagination Off-by-One (memos/gitea pattern)

## Source
Inspired by pagination bugs in memos and gitea — 1-indexed page number used
as if 0-indexed. This style of off-by-one is a common harness-bench v2 pattern.

## Goal
Fix `src/paginator.py` so `paginate()` uses 1-indexed page numbers correctly.

## The bug
```python
# Current — page 1 returns items starting at index per_page, not 0:
start = page * per_page          # wrong: page=1, per_page=3 → start=3

# Fix — subtract 1:
start = (page - 1) * per_page   # correct: page=1, per_page=3 → start=0
```

## All 7 tests must pass
```
test_first_page_starts_at_zero    ← currently FAILS (returns [3,4,5])
test_second_page                  ← currently FAILS (returns [6,7,8])
test_third_page                   ← currently FAILS (returns [9])
test_last_partial_page            ← currently FAILS (returns [])
test_empty_list                   ← passes
test_single_item                  ← FAILS (returns [])
test_total_pages                  ← passes
```
