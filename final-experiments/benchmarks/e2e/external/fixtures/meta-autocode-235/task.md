# TASK-235: Fix get_stash_count Reads Wrong Key (lazygit pattern)

## Source
Inspired by jesseduffield/lazygit stash display. Reading 'count' instead
of 'entries' always returns 0.

## Goal
Fix `src/stash_info.py` so `get_stash_count()` reads the `'entries'` key.

## The bug
```python
# BUG: wrong key 'count'
return stash_info.get('count', 0)

# Fix:
return stash_info.get('entries', 0)
```

## Failing tests (3/7 fail initially)
```
test_entries_three   ← FAILS ({'entries':3} → bug:0, correct:3)
test_entries_with_name ← FAILS ({'entries':5,'name':'wip'} → bug:0, correct:5)
test_entries_vs_count ← FAILS ({'entries':1,'count':0} → bug:0, correct:1)
```
