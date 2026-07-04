# TASK-158: Fix Relative Path Detection Missing Parent Dir (vite pattern)

## Source
Inspired by vitejs/vite module resolution. Relative path check only handles
`./` but misses `../` paths, treating parent-relative imports as non-relative.

## Goal
Fix `src/module_resolver.py` so `is_relative_path()` also recognizes `../`
paths as relative.

## The bug
```python
# BUG: only checks './' — '../' paths return False
return path.startswith('./')

# Fix:
return path.startswith('./') or path.startswith('../')
```

## Failing tests (3/7 fail initially)
```
test_parent_dir   ← FAILS (False instead of True for '../parent')
test_grandparent  ← FAILS (False instead of True for '../../grandparent')
test_sibling      ← FAILS (False instead of True for '../sibling/file.js')
```
