# Task: Implement a Deterministic Stable Sort

## Objective

Implement a sorting function that produces identical output every time, even when items have equal sort keys. The sort must be stable and deterministic — tie-breaking must use a consistent secondary key.

## Requirements

1. Implement `deterministic_sort(items, key)` in `project/sorter.py`.
2. When items have equal primary keys, break ties by the item's original index (stable sort).
3. Output must be exactly the same every run — byte-for-byte identical.
4. All tests in `project/test_sorter.py` must pass.

## Files

- `project/sorter.py` — implement the sort function here
- `project/test_sorter.py` — test file with deterministic assertions
- `project/test_data.json` — test data with ties
