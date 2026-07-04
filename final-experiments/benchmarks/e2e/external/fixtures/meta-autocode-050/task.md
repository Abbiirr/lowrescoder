# TASK-050: Fix Client Env Var Prefix Filter (vitejs/vite pattern)

## Source
Inspired by vitejs/vite's `VITE_` prefix requirement: only env vars prefixed
with `VITE_` are exposed to client-side code. Exposing all env vars leaks
secrets like database passwords and API keys.

## Goal
Fix `src/env_filter.py` so `get_client_env_vars()` returns only the entries
whose key starts with `'VITE_'`.

## The bug
```python
# BUG: returns all env vars — exposes secrets
return env_vars.copy()

# Fix: filter by prefix
return {k: v for k, v in env_vars.items() if k.startswith('VITE_')}
```

## Failing tests (3/7 fail initially)
```
test_non_vite_excluded            ← FAILS (DATABASE_URL, SECRET_KEY leaked)
test_all_non_vite_returns_empty   ← FAILS (all vars returned, expected {})
test_lowercase_vite_prefix_excluded ← FAILS ('vite_secret' leaked)
```
