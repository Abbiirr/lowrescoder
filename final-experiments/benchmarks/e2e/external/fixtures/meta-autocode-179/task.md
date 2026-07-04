# TASK-179: Fix Public Memo Counter Ignores Visibility (memos pattern)

## Source
Inspired by usememos/memos memo visibility filtering. The counter uses
`len(memos)` instead of filtering by visibility, so private memos are
incorrectly included in the public count.

## Goal
Fix `src/memo_visibility.py` so `count_public_memos()` only counts memos
whose `visibility` field equals `'PUBLIC'`.

## The bug
```python
# BUG: counts all memos — ignores visibility
return len(memos)

# Fix:
return sum(1 for m in memos if m.get('visibility') == 'PUBLIC')
```

## Failing tests (3/7 fail initially)
```
test_all_private      ← FAILS (2 private memos → bug returns 2, not 0)
test_mixed_visibility ← FAILS (1 public + 1 private → bug returns 2, not 1)
test_single_private   ← FAILS (1 private memo → bug returns 1, not 0)
```
