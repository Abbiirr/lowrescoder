# TASK-194: Fix Admin Check Misses Owner Role (gitea pattern)

## Source
Inspired by go-gitea/gitea permission checking. Checking only `role == 'admin'`
misses the `'owner'` role, which also has admin-level access.

## Goal
Fix `src/role_checker.py` so `is_admin()` accepts both `'admin'` and
`'owner'` roles.

## The bug
```python
# BUG: misses 'owner'
return user.get('role') == 'admin'

# Fix:
return user.get('role') in ('admin', 'owner')
```

## Failing tests (3/7 fail initially)
```
test_owner_role         ← FAILS ('owner' not recognized — bug False)
test_owner_with_username ← FAILS (same — extra field doesn't matter)
test_owner_with_id      ← FAILS (same)
```
