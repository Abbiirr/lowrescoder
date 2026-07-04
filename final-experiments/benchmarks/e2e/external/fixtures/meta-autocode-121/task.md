# TASK-121: Fix Cache Invalidator Tag Lookup (usememos/memos pattern)

## Source
Inspired by usememos/memos cache invalidation logic. When invalidating by
multiple tags, reassigning instead of extending causes only the last tag's
keys to be removed.

## Goal
Fix `src/cache_invalidator.py` so `invalidate_keys()` removes cache entries
for ALL specified tags, not just the last one.

## The bug
```python
# BUG: overwrites on each iteration — only last tag's keys survive to removal
keys_to_remove = tag_index.get(tag, [])

# Fix: extend the list
keys_to_remove.extend(tag_index.get(tag, []))
```

## Failing tests (3/7 fail initially)
```
test_both_tags_removed    ← FAILS (first tag's key survives)
test_first_tag_key_removed ← FAILS (k1 not removed)
test_three_tags_all_removed ← FAILS (only last tag's key gone)
```
