# Task: Handle Disk-Full Errors in File Writer

## Objective

The `writer.py` module writes data to files but doesn't handle `OSError` when the disk is full. Add graceful error handling: clean up partial writes, report the error, and don't leave corrupt files behind.

## Requirements

1. Wrap file write operations in proper error handling for `OSError`.
2. If a write fails (disk full), remove any partially written file.
3. The function should raise a clear, descriptive exception after cleanup.
4. Do not propagate a bare `OSError`; either handle it without raising or raise a different exception type with a descriptive message.
5. All tests in `test_writer.py` must pass.

## Current State

- `writer.py` — `write_report(path, data)` writes JSON to a file with no error handling.
- `test_writer.py` — tests that mock `OSError` for disk-full scenarios.

## Files

- `writer.py` — add disk-full error handling
- `test_writer.py` — test file (do not modify)
