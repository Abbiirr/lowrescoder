# Task: Fix an Off-by-One Error

## Objective

The file `counter.py` has an off-by-one error in the `count_items` function. It uses `<` where it should use `<=`, causing the function to miss the last item. Fix the bug with minimal changes.

## Requirements

1. Fix the comparison operator in `count_items` so it includes the `end` boundary.
2. The existing test in `test_counter.py` must pass.
3. The fix should be exactly 1 line changed — no refactoring, no restructuring.

## Current State

- `counter.py` — contains `count_items(start, end)` that iterates with `<` instead of `<=`.
- `test_counter.py` — tests that verify correct inclusive behavior. Currently failing.

## Files

- `counter.py` — the module to fix (one character change)
- `test_counter.py` — test file (do not modify)
