# Task: Fix Unicode Crash in Search Function

## Objective

The search module in `project/search.py` crashes when users type non-ASCII characters (e.g., accented letters, CJK characters, emoji). Fix the search function so it handles all Unicode input correctly.

## Requirements

1. The `search()` function must accept any Unicode string without crashing.
2. Case-insensitive search must work for Unicode characters (e.g., searching "cafe" matches "Caf\u00e9").
3. All existing tests in `project/test_search.py` must pass.
4. Do not change the function signatures or return types.

## Current State

- `project/search.py` contains a `search(query, items)` function that works for ASCII but crashes on Unicode.
- `project/test_search.py` has test cases including Unicode strings that currently fail.

## Files

- `project/search.py` — the buggy search module
- `project/test_search.py` — test file with Unicode test cases
