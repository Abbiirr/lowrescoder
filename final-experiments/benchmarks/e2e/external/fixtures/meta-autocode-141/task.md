# TASK-141: Fix Repository Fork Count Increment (go-gitea/gitea pattern)

## Source
Inspired by gitea repository forking. Fork count is decremented instead
of incremented when a new fork is created.

## Goal
Fix `src/repo_forker.py` so `fork_repository()` increments `fork_count`.

## The bug
```python
# BUG: decrements
repo['fork_count'] = repo.get('fork_count', 0) - 1

# Fix:
repo['fork_count'] = repo.get('fork_count', 0) + 1
```

## Failing tests (3/7 fail initially)
```
test_fork_count_incremented   ← FAILS (4 instead of 6)
test_fork_count_starts_at_zero ← FAILS (-1 instead of 1)
test_multiple_forks           ← FAILS (0 instead of 4)
```
