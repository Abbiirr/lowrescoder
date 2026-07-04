# TASK-225: Fix get_port Reads Wrong Config Key (vite pattern)

## Source
Inspired by vitejs/vite server configuration. Reading 'server_port' instead
of 'port' silently returns the default regardless of user config.

## Goal
Fix `src/server_config.py` so `get_port()` reads the `'port'` key.

## The bug
```python
# BUG: wrong key 'server_port'
return config.get('server_port', default)

# Fix:
return config.get('port', default)
```

## Failing tests (3/7 fail initially)
```
test_port_8080    ← FAILS ({'port':8080} → bug:3000, correct:8080)
test_port_5173    ← FAILS ({'port':5173} → bug:3000, correct:5173)
test_port_with_host ← FAILS ({'port':4000,'host':'0.0.0.0'} → bug:3000)
```
