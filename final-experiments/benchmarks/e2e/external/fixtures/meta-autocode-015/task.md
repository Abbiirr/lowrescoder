# TASK-015: Fix Config Deep Merge (vitejs/vite pattern)

## Source
Inspired by vitejs/vite config resolution.
vite merges user config over internal defaults. A shallow merge (`{**base, **override}`)
silently drops sibling keys inside nested sections.

## Goal
Fix `src/config_merger.py` so `merge_config()` recursively merges nested dicts
instead of replacing them wholesale.

## The bug
```python
# BUG: replaces nested dicts entirely
return {**base, **override}

# Fix: recurse when both values are dicts
def merge_config(base, override):
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_config(result[key], value)
        else:
            result[key] = value
    return result
```

## Failing tests (3/7 fail initially)
```
test_nested_preserves_sibling_keys  ← FAILS (host dropped)
test_nested_override_value          ← FAILS (outDir dropped)
test_deep_nesting                   ← FAILS (# alias dropped)
```
