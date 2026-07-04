# TASK-230: Fix count_watchers Reads stargazers_count Not watchers_count (gitea pattern)

## Source
Inspired by go-gitea/gitea repository statistics. Reading 'stargazers_count'
instead of 'watchers_count' returns star count instead of watcher count.

## Goal
Fix `src/watcher_counter.py` so `count_watchers()` returns the value of
`'watchers_count'`.

## The bug
```python
# BUG: wrong key
return repo.get('stargazers_count', 0)

# Fix:
return repo.get('watchers_count', 0)
```

## Failing tests (3/7 fail initially)
```
test_watchers_five    ← FAILS ({'watchers_count':5} → bug:0, correct:5)
test_watchers_vs_stars ← FAILS ({'watchers_count':10,'stargazers_count':50} → bug:50)
test_watchers_three   ← FAILS ({'watchers_count':3,...} → bug:0, correct:3)
```
