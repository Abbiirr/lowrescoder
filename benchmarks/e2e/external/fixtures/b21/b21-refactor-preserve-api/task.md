# Task: Refactor Internal Implementation, Preserve Public API

## Objective

Refactor the messy internal implementation of `mathutils.py` while keeping the public API (function names, signatures, return values) identical.

## Requirements

1. All 6 existing tests in `test_mathutils.py` must pass without modification.
2. The 3 public function signatures must remain unchanged: `calculate_stats(numbers)`, `normalize(numbers)`, `find_outliers(numbers, threshold=2.0)`.
3. The internal code should be cleaner: remove code duplication, extract helper functions, or improve readability.
4. The module must still be importable as `from mathutils import calculate_stats, normalize, find_outliers`.

## Current State

- `mathutils.py` — Module with 3 public functions. Implementation has duplicated mean/stddev calculations, inline magic numbers, and deeply nested logic.
- `test_mathutils.py` — 6 tests (2 per function) that verify correctness.

## Files

- `mathutils.py` — Module to refactor (public API must not change)
- `test_mathutils.py` — Tests that must continue to pass
