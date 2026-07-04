# TASK-095: Fix Memo Visibility Protected Role Check (usememos/memos pattern)

## Source
Inspired by usememos/memos visibility control. A 'protected' memo should only
be visible to 'member' and 'admin' roles — not 'public'.

## Goal
Fix `src/memo_visibility.py` so `can_view_memo()` removes 'public' from the
allowed roles for 'protected' visibility.

## The bug
```python
# BUG: 'public' role incorrectly allowed for protected memos
return viewer_role in ('member', 'admin', 'public')

# Fix:
return viewer_role in ('member', 'admin')
```

## Failing tests (3/7 fail initially)
```
test_protected_not_visible_to_public_role  ← FAILS (True != False)
test_protected_default_visibility_public   ← FAILS (True != False)
test_protected_memo_public_role_blocked    ← FAILS (True != False)
```
