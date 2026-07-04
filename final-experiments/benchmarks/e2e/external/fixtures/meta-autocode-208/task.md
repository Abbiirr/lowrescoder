# TASK-208: Fix Main Branch Check Uses startswith Instead of Equality (lazygit pattern)

## Source
Inspired by jesseduffield/lazygit branch detection. Using
`startswith('main')` falsely matches branch names like `'mainline'` or
`'main-branch'`.

## Goal
Fix `src/branch_checker.py` so `is_main_branch()` uses exact equality.

## The bug
```python
# BUG: prefix match — too broad
return branch_name.startswith('main')

# Fix:
return branch_name == 'main'
```

## Failing tests (3/7 fail initially)
```
test_mainline      ← FAILS ('mainline' starts with 'main' → bug True)
test_main_branch   ← FAILS ('main-branch' → bug True)
test_main2         ← FAILS ('main2' → bug True)
```
