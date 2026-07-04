# TASK-127: Fix Response Timer Subtraction Order (axios/axios pattern)

## Source
Inspired by axios request timing. Subtracts in the wrong order
(start - end) returning a negative elapsed time.

## Goal
Fix `src/response_timer.py` so `compute_elapsed_ms()` returns a positive
elapsed time (end - start).

## The bug
```python
# BUG: wrong order — returns negative elapsed
elapsed_s = start_ts - end_ts

# Fix:
elapsed_s = end_ts - start_ts
```

## Failing tests (3/7 fail initially)
```
test_positive_elapsed ← FAILS (-1000.0 instead of 1000.0)
test_small_gap        ← FAILS (-100.0 instead of 100.0)
test_typical_request  ← FAILS (-250.0 instead of 250.0)
```
