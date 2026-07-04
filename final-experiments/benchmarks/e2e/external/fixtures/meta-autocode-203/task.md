# TASK-203: Fix Fork Permission Check Requires Write Instead of Read (gitea pattern)

## Source
Inspired by go-gitea/gitea repository access control. Forking a repo only
requires read access, but the check requires write or admin permission.

## Goal
Fix `src/fork_checker.py` so `can_fork()` allows users with read, write, or
admin permission.

## The bug
```python
# BUG: requires write/admin — read is sufficient for forking
return user.get('permission') in ('write', 'admin')

# Fix:
return user.get('permission') in ('read', 'write', 'admin')
```

## Failing tests (3/7 fail initially)
```
test_read_can_fork    ← FAILS ('read' permission denied — bug False)
test_read_with_id     ← FAILS (same — extra fields irrelevant)
test_read_with_username ← FAILS (same)
```
