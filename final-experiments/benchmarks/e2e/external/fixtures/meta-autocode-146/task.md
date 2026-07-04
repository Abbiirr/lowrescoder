# TASK-146: Fix Tag Merger Union vs Intersection (langflow-ai/langflow pattern)

## Source
Inspired by langflow tag aggregation. Returns intersection (&) of tag sets
instead of union (|), losing unique tags from each set.

## Goal
Fix `src/tag_merger.py` so `merge_tag_sets()` returns the union of both sets.

## The bug
```python
# BUG: intersection — only tags in BOTH sets
return set_a & set_b

# Fix: union — tags in EITHER set
return set_a | set_b
```

## Failing tests (3/7 fail initially)
```
test_disjoint_sets               ← FAILS ({} instead of {'a','b'})
test_unique_elements_from_a_included ← FAILS ('alpha' not in result)
test_all_unique_elements         ← FAILS ({'q'} instead of {'p','q','r'})
```
