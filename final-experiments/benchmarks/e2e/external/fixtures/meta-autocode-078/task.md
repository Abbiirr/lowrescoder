# TASK-078: Fix Team Permission Level Check (go-gitea/gitea pattern)

## Source
Inspired by go-gitea/gitea team access control. Permission levels are
hierarchical: level 5 (Owner) implies level 3 (Write) implies level 1 (Read).
The bug uses equality (`==`), so an Owner (level 5) fails a check requiring
Write (level 3).

## Goal
Fix `src/permission_checker.py` so `user_has_permission()` uses `>=` to
allow higher levels to satisfy lower requirements.

## The bug
```python
# BUG: exact match only
return user_level == required_level

# Fix: level hierarchy
return user_level >= required_level
```

## Failing tests (3/7 fail initially)
```
test_higher_level_grants_access  ← FAILS (level=4, required=2 → False, should be True)
test_admin_has_write_permission  ← FAILS (level=5, required=3 → False, should be True)
test_owner_has_read_permission   ← FAILS (level=10, required=1 → False, should be True)
```
