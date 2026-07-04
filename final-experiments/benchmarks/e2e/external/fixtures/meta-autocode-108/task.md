# TASK-108: Fix File Watcher Extension Dot Normalization (vitejs/vite pattern)

## Source
Inspired by vitejs/vite file watching. Extensions should be stored without
leading dot for consistent comparisons.

## Goal
Fix `src/file_watcher.py` so `get_watched_extensions()` strips leading `.`
from each extension.

## The bug
```python
# BUG: no normalization
return set(raw)

# Fix:
return {ext.lstrip('.') for ext in raw}
```

## Failing tests (3/7 fail initially)
```
test_dot_prefix_stripped         ← FAILS ('py' not in {'.py', '.js'})
test_mixed_dot_no_dot_normalized ← FAILS ({'.py', 'js'} != {'py', 'js'})
test_dot_extension_not_in_result ← FAILS ('.ts' IS in result)
```
