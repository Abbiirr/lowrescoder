# TASK-124: Fix Plugin Registry Case-Insensitive Lookup (vitejs/vite pattern)

## Source
Inspired by vite plugin resolution. Plugin names should be looked up
case-insensitively, but the registry uses exact case matching.

## Goal
Fix `src/plugin_registry.py` so `get_plugin()` finds plugins regardless
of the case used during registration.

## The bug
```python
# BUG: exact case lookup
return _registry.get(name)

# Fix: normalize to lowercase on both register and lookup
# In register_plugin: _registry[name.lower()] = handler
# In get_plugin: return _registry.get(name.lower())
```

## Failing tests (3/7 fail initially)
```
test_lookup_different_case ← FAILS ('myplugin' != 'MyPlugin')
test_lookup_upper_case     ← FAILS ('FORMATTER' != 'formatter')
test_lookup_mixed_case     ← FAILS ('dataloader' != 'DataLoader')
```
