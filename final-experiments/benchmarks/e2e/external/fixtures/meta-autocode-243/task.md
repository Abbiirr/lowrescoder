# TASK-243: Fix get_base_url() Wrong Key 'base_url' vs 'base' (vite pattern)

## Source
Inspired by vitejs/vite config reading. Vite uses `base` in its config, not `base_url`.

## Goal
Fix `src/base_url_reader.py` so `get_base_url()` reads the correct `'base'` key.

## The bug
```python
# BUG: wrong key
return config.get('base_url', default)

# Fix:
return config.get('base', default)
```

## Failing tests (3/7 fail initially)
```
test_base_app      ← FAILS ({'base': '/app'} → bug:'/', correct:'/app')
test_base_subdir   ← FAILS ({'base': '/subdir'} → bug:'/', correct:'/subdir')
test_base_relative ← FAILS ({'base': './'} → bug:'/', correct:'./')
```
