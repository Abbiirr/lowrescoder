# TASK-125: Fix Path Normalizer Backslash Handling (sharkdp/bat pattern)

## Source
Inspired by bat's cross-platform path normalization. Backslashes from
Windows-style paths are not converted to forward slashes.

## Goal
Fix `src/path_normalizer.py` so `normalize_path()` converts backslashes
to forward slashes before collapsing multiple slashes.

## The bug
```python
# BUG: only collapses multiple forward slashes, ignores backslashes
path = re.sub(r'/+', '/', path)

# Fix: convert backslashes first
path = path.replace('\\', '/')
path = re.sub(r'/+', '/', path)
```

## Failing tests (3/7 fail initially)
```
test_backslash_converted ← FAILS (backslashes not converted)
test_mixed_slashes       ← FAILS (backslash remains)
test_windows_absolute    ← FAILS (Windows path unchanged)
```
