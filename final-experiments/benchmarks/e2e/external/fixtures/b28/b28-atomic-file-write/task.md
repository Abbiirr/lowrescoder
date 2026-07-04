# Task: Implement Atomic File Write

## Objective

Implement a function that atomically updates a file so that a reader never sees a partially-written file. Use the write-to-temp-then-rename pattern.

## Requirements

1. Implement `atomic_write(path, content)` in `project/atomic.py`.
2. Write content to a temporary file first, then rename to the target path.
3. If the write fails midway, the original file must remain unchanged.
4. The function must use `os.replace()` or `os.rename()` for the atomic swap.
5. All tests in `project/test_atomic.py` must pass.

## Files

- `project/atomic.py` — implement the atomic writer here
- `project/test_atomic.py` — test file
