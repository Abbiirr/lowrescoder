# TASK-074: Fix Archived Memo Filtering (usememos/memos pattern)

## Source
Inspired by usememos/memos memo list API. When `include_archived=False` (the
default), archived memos should be excluded from results. The bug returns all
memos regardless of the `include_archived` parameter.

## Goal
Fix `src/memo_filter.py` so `filter_memos()` excludes memos where
`archived=True` when `include_archived=False`.

## The bug
```python
# BUG: returns all memos
return memos

# Fix: filter when requested
if not include_archived:
    return [m for m in memos if not m.get('archived', False)]
return memos
```

## Failing tests (3/7 fail initially)
```
test_archived_excluded_by_default ← FAILS (archived memo included by default)
test_mixed_archived_excluded      ← FAILS (archived memo not filtered out)
test_all_archived_returns_empty   ← FAILS (all archived → returns 2, expected [])
```
