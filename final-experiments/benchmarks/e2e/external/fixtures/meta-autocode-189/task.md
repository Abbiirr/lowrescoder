# TASK-189: Fix Extension Removal Splits on First Dot (vite pattern)

## Source
Inspired by vitejs/vite module file resolution. Using `split('.')[0]` removes
everything after the first dot, so `'app.test.js'` incorrectly becomes
`'app'` instead of `'app.test'`.

## Goal
Fix `src/path_utils.py` so `remove_extension()` only removes the last
extension (last dot segment).

## The bug
```python
# BUG: removes at first dot
return filename.split('.')[0]

# Fix:
return filename.rsplit('.', 1)[0]
```

## Failing tests (3/7 fail initially)
```
test_test_file   ← FAILS ('app.test.js' → bug 'app', should 'app.test')
test_spec_file   ← FAILS ('component.spec.ts' → bug 'component')
test_config_file ← FAILS ('my.vite.config.js' → bug 'my')
```
