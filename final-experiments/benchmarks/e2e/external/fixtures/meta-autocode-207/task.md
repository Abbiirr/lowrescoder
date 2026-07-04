# TASK-207: Fix Env Var Resolver Ignores Default Argument (vite pattern)

## Source
Inspired by vitejs/vite environment configuration. Using `config.get(key)`
without passing the `default` argument always returns `None` for missing keys.

## Goal
Fix `src/env_resolver.py` so `get_env_var()` forwards the `default`
argument to `dict.get()`.

## The bug
```python
# BUG: default parameter ignored
return config.get(key)

# Fix:
return config.get(key, default)
```

## Failing tests (3/7 fail initially)
```
test_missing_with_default     ← FAILS (missing key → bug None, should '8080')
test_missing_in_partial_config ← FAILS (same)
test_missing_bool_default     ← FAILS (missing → bug None, should False)
```
