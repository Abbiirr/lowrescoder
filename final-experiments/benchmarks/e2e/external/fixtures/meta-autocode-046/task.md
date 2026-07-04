# TASK-046: Fix Path Traversal Guard (go-gitea/gitea pattern)

## Source
Inspired by go-gitea/gitea file path security validation. The guard should
block paths with `..` as a path COMPONENT (e.g., `../secret` or `a/../b`)
but allow `..` as a substring within a filename (e.g., `file..txt`). The bug
uses a string substring check, blocking valid filenames.

## Goal
Fix `src/path_guard.py` so `is_safe_path()` checks path components, not
substrings.

## The bug
```python
# BUG: '..' in path blocks 'file..txt' (legitimate)
if '..' in path:
    return False

# Fix: only block when '..' is a standalone component
if any(part == '..' for part in path.replace('\\', '/').split('/')):
    return False
```

## Failing tests (3/7 fail initially)
```
test_double_dot_in_filename  ← FAILS ('file..txt' blocked)
test_double_dot_in_extension ← FAILS ('app..min.js' blocked)
test_ellipsis_in_dirname     ← FAILS ('src/helpers..utils/main.py' blocked)
```
