# TASK-221: Fix is_repo_archived Reads Wrong Key (gitea pattern)

## Source
Inspired by go-gitea/gitea repository state. Reading 'is_archive' instead
of 'archived' always returns False even for archived repositories.

## Goal
Fix `src/repo_checker.py` so `is_repo_archived()` reads the correct
`'archived'` key.

## The bug
```python
# BUG: wrong key 'is_archive'
return bool(repo.get('is_archive'))

# Fix:
return bool(repo.get('archived'))
```

## Failing tests (3/7 fail initially)
```
test_archived_true      ← FAILS ({'archived':True} → bug:False, correct:True)
test_archived_with_name ← FAILS ({'archived':True,'name':'oldrepo'} → bug:False)
test_archived_one       ← FAILS ({'archived':1} → bug:False, correct:True)
```
