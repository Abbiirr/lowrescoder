# TASK-048: Fix Repository Fork Count Increment (go-gitea/gitea pattern)

## Source
Inspired by go-gitea/gitea repository forking logic. When a user forks a
repository, the parent's `fork_count` field should increment by 1. The bug
is a no-op assignment (`x = x`) instead of an increment (`x += 1`).

## Goal
Fix `src/fork_counter.py` so `fork_repository()` increments `repo['fork_count']`
by 1 each time it is called.

## The bug
```python
# BUG: no-op — fork_count never changes
repo['fork_count'] = repo['fork_count']

# Fix: increment
repo['fork_count'] += 1
```

## Failing tests (3/7 fail initially)
```
test_fork_increments_from_zero     ← FAILS (0 stays 0, should be 1)
test_fork_increments_from_existing ← FAILS (5 stays 5, should be 6)
test_multiple_forks_accumulate     ← FAILS (0 stays 0 after 3 forks, should be 3)
```
