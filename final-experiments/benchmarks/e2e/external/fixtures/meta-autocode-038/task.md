# TASK-038: Fix Pagination Total Count (go-gitea/gitea pattern)

## Source
Inspired by go-gitea/gitea REST API pagination. The API response includes a
`total` count so clients can calculate page count and show "Page 2 of 4".
The bug uses `len(page_items)` (current page size) instead of the full
collection length, so the total varies by page and is always wrong.

## Goal
Fix `src/paginator.py` so the `total` key in the result reflects the length
of the full `items` collection.

## The bug
```python
# BUG: returns the current page's item count, not the full total
'total': len(page_items),

# Fix: total is the full collection
'total': len(items),
```

## Failing tests (3/7 fail initially)
```
test_total_reflects_full_collection  ← FAILS (page1 total = 3, not 10)
test_total_same_on_page2             ← FAILS (page2 total = 3, not 10)
test_total_correct_on_last_partial_page ← FAILS (last page total = 1, not 10)
```
