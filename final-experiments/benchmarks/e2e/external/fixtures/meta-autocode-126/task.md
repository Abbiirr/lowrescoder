# TASK-126: Fix Permission Checker AND Logic (langflow-ai/langflow pattern)

## Source
Inspired by langflow permission gating. Using `any()` (OR) instead of
`all()` (AND) allows access when a user has ANY required permission
rather than ALL of them.

## Goal
Fix `src/permission_checker.py` so `has_permission()` requires ALL
specified permissions to be present.

## The bug
```python
# BUG: any() — passes if user has at least one required permission
return any(perm in user_perms for perm in required_permissions)

# Fix:
return all(perm in user_perms for perm in required_permissions)
```

## Failing tests (3/7 fail initially)
```
test_has_first_not_second  ← FAILS (partial match incorrectly allowed)
test_has_last_not_first    ← FAILS (partial match incorrectly allowed)
test_one_of_three_missing  ← FAILS (missing 'admin' not enforced)
```
