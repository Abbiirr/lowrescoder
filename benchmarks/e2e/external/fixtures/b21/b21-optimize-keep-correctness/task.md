# Task: Optimize Slow Algorithm While Keeping Identical Results

## Objective

Optimize the slow sorting and processing functions in `processor.py` while keeping output byte-for-byte identical. The current implementation uses intentionally naive algorithms.

## Requirements

1. All 5 existing tests in `test_processor.py` must pass without modification.
2. The output of each function must be identical to the original.
3. The public function signatures must not change: `custom_sort(items)`, `find_duplicates(items)`, `group_by_key(items, key_fn)`.
4. The code should be measurably faster (or at least not slower) for large inputs.

## Current State

- `processor.py` — Module with 3 functions using O(n^2) or worse algorithms.
- `test_processor.py` — 5 tests verifying correctness.

## Hints

- `custom_sort` uses bubble sort — any O(n log n) sort is fine.
- `find_duplicates` uses nested loops — a set-based approach is O(n).
- `group_by_key` rebuilds the list for every unique key — a single-pass dict approach is O(n).

## Files

- `processor.py` — Module to optimize
- `test_processor.py` — Tests that must continue to pass
