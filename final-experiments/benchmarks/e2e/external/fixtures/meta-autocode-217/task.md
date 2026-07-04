# TASK-217: Fix is_detached_head Reads Wrong Key (lazygit pattern)

## Source
Inspired by jesseduffield/lazygit HEAD state detection. Reading 'detached'
instead of 'is_detached' always returns False even when HEAD is detached.

## Goal
Fix `src/head_checker.py` so `is_detached_head()` reads the correct
`'is_detached'` key.

## The bug
```python
# BUG: wrong key 'detached'
return bool(head_info.get('detached'))

# Fix:
return bool(head_info.get('is_detached'))
```

## Failing tests (3/7 fail initially)
```
test_is_detached_true      ← FAILS ({'is_detached':True} → bug:False, correct:True)
test_is_detached_with_hash ← FAILS ({'is_detached':True,'hash':'abc1234'} → bug:False)
test_is_detached_one       ← FAILS ({'is_detached':1} → bug:False, correct:True)
```
