# TASK-188: Fix Pinned Check Wrong Field Name (memos pattern)

## Source
Inspired by usememos/memos memo state. The function reads `'pinned'` but the
correct field name in the memo dict is `'is_pinned'`.

## Goal
Fix `src/memo_pin.py` so `is_pinned()` reads the `'is_pinned'` key.

## The bug
```python
# BUG: wrong key 'pinned'
return memo.get('pinned', False)

# Fix:
return memo.get('is_pinned', False)
```

## Failing tests (3/7 fail initially)
```
test_is_pinned_true           ← FAILS ({'is_pinned': True} → bug reads 'pinned'=None → False)
test_pinned_false_is_pinned_true ← FAILS (wrong key still read)
test_is_pinned_true_with_id   ← FAILS (same wrong key issue)
```
