# TASK-012: Fix File Extension Detection (bat/gitea pattern)

## Source
Inspired by sharkdp/bat file-type detection and go-gitea/gitea syntax highlighting.
Using split('.')[1] instead of split('.')[-1] causes multi-dot filenames to
return the wrong language (second segment, not last extension).

## Goal
Fix `src/file_detector.py` so `detect_language()` uses the last extension.

## The bug
```python
# BUG: [1] = second segment
ext = filename.split(".")[1].lower()   # "config.test.json" → "test"

# Fix: [-1] = last segment
ext = filename.split(".")[-1].lower()  # "config.test.json" → "json"
```

## All 7 tests must pass
```
test_simple_python        ← passes (single dot)
test_simple_json          ← passes (single dot)
test_multi_dot_json       ← FAILS ("config.test.json" → "test" not "json")
test_multi_dot_js         ← FAILS ("app.min.js" → "min" not "javascript")
test_multi_dot_ts         ← FAILS ("main.spec.ts" → "text" not "typescript")
test_no_extension         ← passes
test_unknown_extension    ← passes
```
