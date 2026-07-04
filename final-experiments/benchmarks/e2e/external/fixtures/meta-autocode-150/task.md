# TASK-150: Fix File Extension Extraction (vite pattern)

## Source
Inspired by vitejs/vite asset resolution. Extension parsing uses `rsplit`
without checking whether a dot was found, returning the full filename instead
of an empty string for extension-less files.

## Goal
Fix `src/asset_resolver.py` so `get_extension()` returns `''` for files with
no extension.

## The bug
```python
# BUG: returns full path when no dot exists
return path.rsplit('.', 1)[-1]

# Fix: check split produced two parts
parts = path.rsplit('.', 1)
return parts[1] if len(parts) == 2 else ''
```

## Failing tests (3/7 fail initially)
```
test_no_extension_makefile  ← FAILS ('Makefile' instead of '')
test_no_extension_in_path   ← FAILS ('dist/bundle' instead of '')
test_no_extension_nested    ← FAILS ('src/utils/helpers' instead of '')
```
