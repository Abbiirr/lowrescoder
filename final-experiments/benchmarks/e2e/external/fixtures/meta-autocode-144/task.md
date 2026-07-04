# TASK-144: Fix Paginator Offset Calculation (fastapi/fastapi pattern)

## Source
Inspired by FastAPI pagination endpoints. Uses `page * page_size` instead
of `(page - 1) * page_size`, skipping first-page items.

## Goal
Fix `src/paginator.py` so `get_page_items()` correctly computes the offset
for 1-indexed page numbers.

## The bug
```python
# BUG: off by one page — treats page as 0-indexed
offset = page * page_size

# Fix:
offset = (page - 1) * page_size
```

## Failing tests (3/7 fail initially)
```
test_first_page_correct   ← FAILS ([3,4,5] instead of [0,1,2])
test_single_item_first_page ← FAILS ([] instead of ['only'])
test_second_page_correct  ← FAILS ([6,7,8] instead of [3,4,5])
```
