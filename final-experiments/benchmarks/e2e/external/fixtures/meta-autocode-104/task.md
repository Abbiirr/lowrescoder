# TASK-104: Fix Commit Linter Type Check Inverted (go-gitea/gitea pattern)

## Source
Inspired by go-gitea/gitea commit message linting. The condition is inverted:
it errors on VALID types instead of INVALID ones.

## Goal
Fix `src/commit_linter.py` so `lint_commit_message()` errors when `commit_type`
is NOT in `ALLOWED_TYPES`.

## The bug
```python
# BUG: inverted — errors on valid types
if commit_type in ALLOWED_TYPES:
    errors.append(f'unknown commit type: {commit_type}')

# Fix:
if commit_type not in ALLOWED_TYPES:
    errors.append(f'unknown commit type: {commit_type}')
```

## Failing tests (3/7 fail initially)
```
test_feat_type_valid  ← FAILS (['unknown commit type: feat'] != [])
test_fix_type_valid   ← FAILS (['unknown commit type: fix'] != [])
test_chore_type_valid ← FAILS (['unknown commit type: chore'] != [])
```
