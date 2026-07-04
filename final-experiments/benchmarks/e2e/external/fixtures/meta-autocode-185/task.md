# TASK-185: Fix Repo Name Validator Missing Slash Check (gitea pattern)

## Source
Inspired by go-gitea/gitea repository name validation. The validator rejects
spaces and dots but allows slashes, which would create invalid paths.

## Goal
Fix `src/repo_validator.py` so `is_valid_repo_name()` also rejects names
containing a slash (`/`).

## The bug
```python
# BUG: slash not checked
return ' ' not in name and '.' not in name

# Fix:
return ' ' not in name and '.' not in name and '/' not in name
```

## Failing tests (3/7 fail initially)
```
test_slash_in_name      ← FAILS ('my/repo' → bug True, should False)
test_user_slash_project ← FAILS ('user/project' → bug True, should False)
test_short_slash        ← FAILS ('a/b' → bug True, should False)
```
