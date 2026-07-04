# TASK-111: Fix Page Count Ceiling Division (go-gitea/gitea pattern)

## Source
Inspired by go-gitea/gitea pagination. Page count requires ceiling division
(math.ceil) not floor division (//).

## Goal
Fix `src/page_calculator.py` so `get_page_count()` uses ceiling division.

## The bug
```python
# BUG: floor division loses remainder page
return total_items // page_size

# Fix:
import math
return math.ceil(total_items / page_size)
# Or: return (total_items + page_size - 1) // page_size
```

## Failing tests (3/7 fail initially)
```
test_one_extra_item      ← FAILS (1 != 2)
test_partial_first_page  ← FAILS (0 != 1)
test_nine_items          ← FAILS (2 != 3)
```
