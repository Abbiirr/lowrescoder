# TASK-085: Fix Nested Config Getter None vs Missing (vitejs/vite pattern)

## Source
Inspired by vitejs/vite config resolution. A `None` value in config must be
returned as-is — it must not be confused with a missing key (which returns
the default).

## Goal
Fix `src/config_getter.py` so `get_nested()` distinguishes between a key
that is absent (return default) and a key whose value is None (return None).

## The bug
```python
# BUG: .get() + None check conflates missing key with None value
current = current.get(key)
if current is None:
    return default

# Fix: check key presence first
if key not in current:
    return default
current = current[key]
```

## Failing tests (3/7 fail initially)
```
test_none_value_not_replaced_by_default ← FAILS ('MISSING' != None)
test_nested_none_value_preserved        ← FAILS ('secret' != None)
test_none_value_distinguished_from_missing ← FAILS (True != None)
```
