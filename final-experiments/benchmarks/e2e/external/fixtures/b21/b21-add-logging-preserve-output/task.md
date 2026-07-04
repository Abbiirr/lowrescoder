# Task: Add Logging Without Changing Output

## Objective

Add logging to the data processing pipeline in `pipeline.py` without changing its stdout output. Logs must go to stderr or a log file.

## Requirements

1. Add logging calls that record: when processing starts, how many records are processed, and when processing completes.
2. The stdout output of `python pipeline.py input.csv` must remain **byte-for-byte identical** to the original.
3. Log messages must appear in either stderr or a file called `pipeline.log`.
4. All existing tests in `test_pipeline.py` must pass without modification.
5. Use Python's `logging` module (not bare `print` to stderr).

## Current State

- `pipeline.py` — Data processing script that reads CSV, transforms data, writes to stdout.
- `test_pipeline.py` — Tests that verify the exact stdout output.
- `input.csv` — Sample input data.

## Files

- `pipeline.py` — Script to add logging to
- `test_pipeline.py` — Tests that must continue to pass
- `input.csv` — Input data
