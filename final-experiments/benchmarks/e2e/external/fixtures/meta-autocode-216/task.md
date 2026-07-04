# TASK-216: Fix has_hot_reload Reads Wrong Config Key (vite pattern)

## Source
Inspired by vitejs/vite server config. The HMR config key is 'hot'; reading
'hmr' silently returns False even when hot-module-replacement is enabled.

## Goal
Fix `src/hmr_checker.py` so `has_hot_reload()` reads the `'hot'` key.

## The bug
```python
# BUG: wrong key 'hmr'
return bool(config.get('hmr'))

# Fix:
return bool(config.get('hot'))
```

## Failing tests (3/7 fail initially)
```
test_hot_true          ← FAILS ({'hot': True} → bug:False, correct:True)
test_hot_true_with_port ← FAILS ({'hot': True, 'port': 5173} → bug:False)
test_hot_one           ← FAILS ({'hot': 1} → bug:False, correct:True)
```
