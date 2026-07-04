# TASK-110: Fix Lazy Loader Always Calls Loader (langflow-ai/langflow pattern)

## Source
Inspired by langflow-ai/langflow component lazy loading. The function stores
the value in cache but then ignores it, calling `loader_fn()` again anyway.

## Goal
Fix `src/lazy_loader.py` so `get_or_load()` returns `_cache[key]` when the
key is already cached, never calling `loader_fn` again.

## The bug
```python
if key not in _cache:
    _cache[key] = loader_fn()
result = loader_fn()  # BUG: always calls loader

# Fix:
if key not in _cache:
    _cache[key] = loader_fn()
return _cache[key]
```

## Failing tests (3/7 fail initially)
```
test_loader_called_only_once    ← FAILS (count==2, expected 1)
test_cached_value_returned      ← FAILS (result==2, expected 1)
test_loader_not_called_after_cache ← FAILS (calls==3, expected 1)
```
