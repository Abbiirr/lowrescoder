# Task: Fix a Function Name Typo

## Objective

The module `api.py` defines a function called `calcualte_total` (typo), but the tests and the rest of the codebase expect it to be called `calculate_total`. Fix the typo so the API contract is satisfied.

## Requirements

1. Rename the function from `calcualte_total` to `calculate_total` in `api.py`.
2. The tests in `test_api.py` must pass.
3. Only the function name should change — do not alter the function body or any other code.
4. The helper function `_apply_discount` should NOT be renamed.

## Current State

- `api.py` — defines `calcualte_total` (misspelled) and `_apply_discount`.
- `test_api.py` — imports and tests `calculate_total` (correct spelling). Currently fails with `ImportError`.

## Files

- `api.py` — fix the function name
- `test_api.py` — test file (do not modify)
