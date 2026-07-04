# TASK-168: Fix Access Control — and vs or (memos pattern)

## Source
Inspired by usememos/memos memo permissions. Edit access requires owner OR
admin, but the bug uses `and` — requiring both simultaneously, so owners who
aren't admins (and vice versa) are blocked.

## Goal
Fix `src/access_control.py` so `can_edit_memo()` grants access when the user
is the owner OR is an admin.

## The bug
```python
# BUG: requires both owner AND admin
return user_id == memo_owner_id and is_admin

# Fix:
return user_id == memo_owner_id or is_admin
```

## Failing tests (3/7 fail initially)
```
test_owner_not_admin  ← FAILS (False — owner can't edit without being admin)
test_admin_not_owner  ← FAILS (False — admin can't edit without being owner)
test_owner_of_own_memo ← FAILS (False — owner blocked if not admin)
```
