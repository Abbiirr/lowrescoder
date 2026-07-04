# TASK-209: Fix merge_unique Returns Duplicates (langflow pattern)

## Source
Inspired by langflow-ai/langflow node input merging. Simple list
concatenation keeps duplicate values; merge_unique should deduplicate.

## Goal
Fix `src/list_merger.py` so `merge_unique()` returns only unique items.

## The bug
```python
# BUG: no deduplication
return list1 + list2

# Fix:
return list(dict.fromkeys(list1 + list2))
```

## Failing tests (3/7 fail initially)
```
test_partial_overlap   ← FAILS ([1,2]+[2,3]=[1,2,2,3], should [1,2,3])
test_duplicate_in_first ← FAILS ([1,1]+[1,2]=[1,1,1,2], should [1,2])
test_all_overlap       ← FAILS ([1,2,3]+[1,2]=[1,2,3,1,2])
```
