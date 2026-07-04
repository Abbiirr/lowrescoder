# TASK-244: Fix is_branch_merged() Wrong Key 'is_merged' vs 'merged' (lazygit pattern)

## Source
Inspired by jesseduffield/lazygit branch status checking. Branch info uses 'merged', not 'is_merged'.

## Goal
Fix `src/branch_merged.py` so `is_branch_merged()` reads the correct `'merged'` key.

## The bug
```python
# BUG: wrong key
return bool(branch_info.get('is_merged'))

# Fix:
return bool(branch_info.get('merged'))
```

## Failing tests (3/7 fail initially)
```
test_merged_true      ← FAILS ({'merged': True} → bug:False, correct:True)
test_merged_with_name ← FAILS ({'merged': True, ...} → bug:False, correct:True)
test_merged_with_remote ← FAILS ({'merged': True, ...} → bug:False, correct:True)
```
