# Task: Fix Pagination Off-By-One Error

## Objective

The paginator in `project/paginator.py` has an off-by-one error in page count calculation. It reports one too many pages, and the last page is always empty. Fix the pagination logic.

## Requirements

1. `total_pages()` must return the correct number of pages.
2. The last page must contain items (never return an empty last page).
3. `get_page(n)` must return the correct items for each page.
4. Edge cases: empty data, data that divides evenly by page size.
5. All tests in `project/test_paginator.py` must pass.

## Current State

- `project/paginator.py` has a `Paginator` class with `total_pages()` and `get_page(page_num)` methods.
- The page count is always one more than it should be.
- The last page returned by `get_page()` is always empty.
- `project/test_paginator.py` tests the correct behavior.

## Files

- `project/paginator.py` — the buggy paginator
- `project/test_paginator.py` — test file
