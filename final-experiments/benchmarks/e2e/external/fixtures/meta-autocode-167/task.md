# TASK-167: Fix Deduplication Missing seen.add() (bat pattern)

## Source
Inspired by sharkdp/bat file processing utilities. The `deduplicate()` function
has a `seen` set but never calls `seen.add(item)`, so the set stays empty and
every item passes the `not in seen` check — duplicates are never filtered.

## Goal
Fix `src/list_dedup.py` so `deduplicate()` adds each item to `seen` after
appending.

## The bug
```python
if item not in seen:
    result.append(item)
    # BUG: missing seen.add(item)

# Fix:
if item not in seen:
    result.append(item)
    seen.add(item)
```

## Failing tests (3/7 fail initially)
```
test_adjacent_duplicate    ← FAILS ([1,1,2] instead of [1,2])
test_non_adjacent_duplicate ← FAILS ([1,2,1] instead of [1,2])
test_all_same              ← FAILS ([1,1,1] instead of [1])
```
