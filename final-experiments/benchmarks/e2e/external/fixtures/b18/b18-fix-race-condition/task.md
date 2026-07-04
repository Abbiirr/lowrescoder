# Task: Fix Race Condition in Thread-Safe Counter

## Objective

The counter class in `project/counter.py` is not thread-safe. When accessed concurrently by multiple threads, it produces wrong results due to data races. Fix the counter to be thread-safe.

## Requirements

1. `Counter.increment()` and `Counter.decrement()` must be thread-safe.
2. `Counter.value` must return the correct count after concurrent operations.
3. Use `threading.Lock` (or equivalent) to protect shared state.
4. All tests in `project/test_counter.py` must pass, including the concurrent test.
5. Do not change function signatures.

## Current State

- `project/counter.py` has a `Counter` class with `increment()`, `decrement()`, and `value` property.
- No locking is used, so concurrent increments lose updates.
- `project/test_counter.py` runs 100 threads each incrementing 1000 times; expects 100000 but gets less.

## Files

- `project/counter.py` — the non-thread-safe counter
- `project/test_counter.py` — test file with concurrent tests
