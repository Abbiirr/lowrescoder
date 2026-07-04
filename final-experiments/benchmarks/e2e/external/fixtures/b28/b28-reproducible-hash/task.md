# Task: Implement a Reproducible File Hasher

## Objective

Implement a file hasher that produces consistent SHA-256 hashes for files. The hashes must match expected values exactly and be reproducible across runs.

## Requirements

1. Implement `hash_file(path)` and `hash_directory(dir_path)` in `project/hasher.py`.
2. `hash_file()` returns the SHA-256 hex digest of a file's contents.
3. `hash_directory()` returns a dict mapping filenames to their hashes.
4. Hashes must match expected values provided in `project/expected_hashes.json`.
5. All tests in `project/test_hasher.py` must pass.

## Files

- `project/hasher.py` — implement the hasher here
- `project/test_files/` — directory of files to hash
- `project/expected_hashes.json` — expected hash values
- `project/test_hasher.py` — test file
