# TASK-118: Fix Interceptor Chain Order (axios/axios pattern)

## Source
Inspired by axios request/response interceptor pipeline. Interceptors should
run in the order they were added, not reversed.

## Goal
Fix `src/interceptor_chain.py` so `apply_interceptors()` applies functions
in the original order (left-to-right), not reversed.

## The bug
```python
# BUG: reversed() applies interceptors in wrong order
for interceptor in reversed(interceptors):

# Fix:
for interceptor in interceptors:
```

## Failing tests (3/7 fail initially)
```
test_order_preserved        ← FAILS ((5+10)*2 != (5*2)+10)
test_string_pipeline_order  ← FAILS ('cct' != 'cbt')
test_division_order_matters ← FAILS (4.0 != 4.5)
```
