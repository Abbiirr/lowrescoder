# TASK-082: Fix Repository Unstar Counter (go-gitea/gitea pattern)

## Source
Inspired by go-gitea/gitea repository star toggling. When a user unstars a
repository, the star count must decrement, not increment.

## Goal
Fix `src/repo_star_counter.py` so `toggle_star()` decrements `repo['stars']`
when the user is already in `starred_by`.

## The bug
```python
# BUG: increments on both star and unstar
starred_by.discard(user_id)
repo['stars'] = repo.get('stars', 0) + 1

# Fix: decrement on unstar
repo['stars'] = repo.get('stars', 0) - 1
```

## Failing tests (3/7 fail initially)
```
test_unstar_decrements_count     ← FAILS (2 != 0)
test_star_then_unstar_returns_zero ← FAILS (2 != 0)
test_unstar_from_two_gives_one   ← FAILS (3 != 1)
```
