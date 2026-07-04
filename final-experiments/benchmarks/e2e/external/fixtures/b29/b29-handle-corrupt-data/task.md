# Task: Handle Corrupt Rows in CSV Parser

## Objective

The CSV parser in `parser.py` crashes when it encounters malformed rows (wrong number of columns, empty lines, etc.). Add error handling so it skips bad rows and processes the good ones.

## Requirements

1. The parser must not crash on malformed CSV data.
2. Bad rows (wrong column count, empty, etc.) should be skipped.
3. Good rows must still be parsed correctly.
4. Preserve the existing public return shape: return a list of row dicts.
5. All tests in `test_parser.py` must pass.

## Current State

- `parser.py` — `parse_csv(filepath)` reads a CSV and returns rows as dicts. Crashes on malformed data.
- `data.csv` — contains some valid and some corrupt rows.
- `test_parser.py` — tests for correct parsing and error handling.

## Files

- `parser.py` — add error handling for corrupt rows
- `data.csv` — test data with mixed valid/invalid rows (do not modify)
- `test_parser.py` — test file (do not modify)
