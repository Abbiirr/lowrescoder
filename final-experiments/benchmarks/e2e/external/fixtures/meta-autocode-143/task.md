# TASK-143: Fix Import Resolver Containment Check (vitejs/vite pattern)

## Source
Inspired by vite module resolution. The containment check is reversed:
`path in module_name` (does path contain the module?) instead of
`module_name in path` (does path contain the module?).

## Goal
Fix `src/import_resolver.py` so `resolve_import()` finds paths that
contain the module_name, not module_names that contain the path.

## The bug
```python
# BUG: backwards — asks if path is substring of module_name
if path in module_name:

# Fix: asks if module_name is substring of path
if module_name in path:
```

## Failing tests (3/7 fail initially)
```
test_module_in_path        ← FAILS (path not found when module_name is short)
test_exact_module_match    ← FAILS ('/packages/lodash' not in 'lodash')
test_multiple_paths_correct_one ← FAILS (None returned)
```
