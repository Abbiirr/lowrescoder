# Task: Handle Permission-Denied Errors Gracefully

## Objective

The script `file_reader.py` reads a list of files and processes their contents. It crashes when it encounters a file with no read permissions (`chmod 000`). Add error handling so it skips unreadable files, reports which ones failed, and processes the rest.

## Requirements

1. The script must not crash on `PermissionError`.
2. Unreadable files should be skipped and reported (collected in a list of errors).
3. Readable files must still be processed correctly.
4. The function should return both the processed results and a list of files that couldn't be read.
5. All tests in `test_reader.py` must pass.

## Current State

- `file_reader.py` — `read_all(filepaths)` iterates over files and reads them. No error handling.
- `test_reader.py` — tests with readable and unreadable files.

## Files

- `file_reader.py` — add permission-denied handling
- `test_reader.py` — test file (do not modify)
