# TASK-234: Fix is_dev_mode Reads Wrong Config Key (vite pattern)

## Source
Inspired by vitejs/vite build mode detection. Checking 'env' instead of
'mode' fails when mode is set to 'development' without an explicit 'env' key.

## Goal
Fix `src/build_mode.py` so `is_dev_mode()` reads the `'mode'` key.

## The bug
```python
# BUG: wrong key 'env'
return config.get('env') == 'development'

# Fix:
return config.get('mode') == 'development'
```

## Failing tests (3/7 fail initially)
```
test_mode_only        ← FAILS ({'mode':'development'} → bug:False, correct:True)
test_mode_dev_env_prod ← FAILS ({'mode':'development','env':'production'} → bug:False)
test_mode_dev_with_port ← FAILS ({'mode':'development','port':5173} → bug:False)
```
