# TASK-023: Fix Config Merger Array Concatenation (vitejs/vite pattern)

## Source
Inspired by vitejs/vite `mergeConfig` utility. When merging two vite configs,
array fields (plugins, resolve.conditions, optimizeDeps.include) must be
**concatenated** — base array + override array. The bug replaces the base
array with the override array entirely.

## Goal
Fix `src/config_merger.py` so `merge_vite_config()` concatenates arrays
instead of replacing them.

## The bug
```python
# BUG: arrays are replaced instead of concatenated
result[key] = override[key]

# Fix: check for list type and concat
if isinstance(base[key], list) and isinstance(override[key], list):
    result[key] = base[key] + override[key]
else:
    result[key] = override[key]
```

## Failing tests (3/7 fail initially)
```
test_plugins_concatenated           ← FAILS (gets ['legacy()'], wants ['react()', 'legacy()'])
test_resolve_conditions_concatenated ← FAILS (gets ['browser'], wants ['node', 'browser'])
test_optimizeDeps_include_concatenated ← FAILS (gets ['moment','dayjs'], wants ['lodash','moment','dayjs'])
```
