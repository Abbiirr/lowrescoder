# Task: Add CSV Export

## User Request

"We need to be able to export the report data as CSV"

## Context

There is a report module that generates report data as a list of dictionaries.
The user wants to be able to export this data as a CSV file.

## Files

- `report.py` — report data generation module
- `test_report.py` — existing tests for the report module

## Requirements

- Add an `export_csv` function to `report.py` (or a new module)
- The function should accept the report data and a file path
- Output must be valid CSV with headers matching the dict keys
- All data rows must be present in the output
- Existing tests must continue to pass
