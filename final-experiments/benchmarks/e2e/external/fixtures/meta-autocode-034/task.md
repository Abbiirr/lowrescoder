# TASK-034: Fix Memo Visibility Filter Case Sensitivity (usememos/memos pattern)

## Source
Inspired by usememos/memos visibility filter API. When a client queries memos
by visibility ('public', 'private', 'protected'), the comparison should be
case-insensitive since clients may send any casing. The bug uses strict
equality, so 'public' fails to match memos stored as 'PUBLIC'.

## Goal
Fix `src/memo_visibility.py` so `filter_by_visibility()` matches regardless
of case.

## The bug
```python
# BUG: case-sensitive — 'public' != 'PUBLIC'
return [m for m in memos if m['visibility'] == visibility]

# Fix: normalize both sides
return [m for m in memos if m['visibility'].upper() == visibility.upper()]
```

## Failing tests (3/7 fail initially)
```
test_filter_public_lowercase    ← FAILS ('public' returns [])
test_filter_private_mixed_case  ← FAILS ('Private' returns [])
test_filter_protected_lowercase ← FAILS ('protected' returns [])
```
