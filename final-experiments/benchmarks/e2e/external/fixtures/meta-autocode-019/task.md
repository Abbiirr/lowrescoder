# TASK-019: Fix HTTP Client Interceptor Order (axios/axios pattern)

## Source
Inspired by axios/axios request interceptor dispatch.
axios runs request interceptors in LIFO order — the last interceptor added
is the first to execute. The implementation bug iterates in insertion order
(FIFO), reversing the expected execution sequence.

## Goal
Fix `src/http_client.py` so `request()` iterates interceptors in reverse
(LIFO) order.

## The bug
```python
# BUG: FIFO — runs interceptors in insertion order
for fn in self._interceptors:
    config = fn(config)

# Fix: LIFO — last added runs first
for fn in reversed(self._interceptors):
    config = fn(config)
```

## Failing tests (3/7 fail initially)
```
test_two_interceptors_lifo_order      ← FAILS ([1,2] not [2,1])
test_three_interceptors_lifo_order    ← FAILS ([1,2,3] not [3,2,1])
test_last_added_wins_on_key_conflict  ← FAILS ("second" not "first")
```
