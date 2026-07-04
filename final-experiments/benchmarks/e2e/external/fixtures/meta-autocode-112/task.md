# TASK-112: Fix Port Availability Check Inverted (vitejs/vite pattern)

## Source
Inspired by vitejs/vite dev server port allocation. The availability check
is inverted — returns True when the port IS used, not when it's free.

## Goal
Fix `src/port_allocator.py` so `is_port_available()` returns True when port
is NOT in `used_ports`.

## The bug
```python
# BUG: inverted
return port in used_ports

# Fix:
return port not in used_ports
```

## Failing tests (3/7 fail initially)
```
test_available_port_is_true ← FAILS (False != True)
test_used_port_is_false     ← FAILS (True != False)
test_large_range_available  ← FAILS (False != True)
```
