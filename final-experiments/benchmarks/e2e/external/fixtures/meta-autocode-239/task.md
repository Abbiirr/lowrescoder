# TASK-239: Fix get_default_branch Reads Wrong Key (gitea pattern)

## Source
Inspired by go-gitea/gitea repository API. Reading 'default' instead of
'default_branch' returns the fallback 'main' for all repos.

## Goal
Fix `src/branch_info.py` so `get_default_branch()` reads `'default_branch'`.

## The bug
```python
# BUG: wrong key 'default'
return repo.get('default', 'main')

# Fix:
return repo.get('default_branch', 'main')
```

## Failing tests (3/7 fail initially)
```
test_master  ← FAILS ({'default_branch':'master'} → bug:'main', correct:'master')
test_develop ← FAILS ({'default_branch':'develop',...} → bug:'main')
test_release ← FAILS ({'default_branch':'release','default':'main'} → bug:'main')
```
