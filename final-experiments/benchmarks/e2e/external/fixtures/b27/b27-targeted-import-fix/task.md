# Task: Fix a Broken Import Path

## Objective

The `main.py` file imports `parse_data` from `utils.parser`, but the function was moved to `utils.data_parser`. Fix the import so the program runs correctly.

## Requirements

1. Update the import in `main.py` to point to the correct module (`utils.data_parser`).
2. The program must run without `ImportError`.
3. Only the import line should change — do not restructure the package.
4. Do not create compatibility shims or re-exports.

## Current State

- `main.py` — imports `from utils.parser import parse_data` (broken).
- `utils/data_parser.py` — contains the `parse_data` function.
- `utils/parser.py` — does NOT exist (was removed when the module was renamed).
- Running `python main.py` raises `ModuleNotFoundError`.

## Files

- `main.py` — fix the import line
- `utils/` — package directory (do not modify)
