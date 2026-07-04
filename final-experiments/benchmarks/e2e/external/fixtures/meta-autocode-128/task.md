# TASK-128: Fix Connection Pool Health Check (go-gitea/gitea pattern)

## Source
Inspired by gitea database connection pooling. Connections are returned
without checking the `healthy` flag, so broken connections get handed out.

## Goal
Fix `src/connection_pool.py` so `get_connection()` skips unhealthy
connections and returns the first healthy one (or None if none exist).

## The bug
```python
# BUG: no health check before returning
conn_obj = _pool.pop(i)
return conn_obj

# Fix: check health
if conn.get('healthy'):
    conn_obj = _pool.pop(i)
    return conn_obj
```

## Failing tests (3/7 fail initially)
```
test_unhealthy_connection_skipped ← FAILS (bad conn returned first)
test_only_unhealthy_returns_none  ← FAILS (unhealthy conn returned)
test_skips_multiple_unhealthy     ← FAILS (returns id=1 instead of id=3)
```
