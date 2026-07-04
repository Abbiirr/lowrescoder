# TASK-200: Fix Overlapping Keys Uses Equality Instead of Intersection (langflow pattern)

## Source
Inspired by langflow-ai/langflow node configuration merging. Using `==` on
key sets requires both dicts to have identical keys, so partial overlaps
(one dict has extra keys) are incorrectly reported as non-overlapping.

## Goal
Fix `src/dict_utils.py` so `have_overlapping_keys()` returns True when at
least one key is shared (intersection, not equality).

## The bug
```python
# BUG: equality — both must have identical key sets
return set(d1.keys()) == set(d2.keys())

# Fix:
return bool(set(d1.keys()) & set(d2.keys()))
```

## Failing tests (3/7 fail initially)
```
test_one_extra_key     ← FAILS ({'a'} vs {'a','b'} — overlap 'a' but sets differ)
test_partial_overlap   ← FAILS ({'a','c'} vs {'a','b'} — overlap 'a')
test_extra_key_other_side ← FAILS ({'x'} vs {'x','y'} — overlap 'x')
```
