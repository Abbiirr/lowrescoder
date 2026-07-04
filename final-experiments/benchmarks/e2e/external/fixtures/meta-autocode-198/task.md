# TASK-198: Fix Bare Import Classifier Misses '../' Relative Paths (vite pattern)

## Source
Inspired by vitejs/vite module import resolution. Only checking
`startswith('./')` lets `'../utils'` and `'../../shared'` be misclassified as
bare (package) imports instead of relative ones.

## Goal
Fix `src/import_classifier.py` so `is_bare_import()` also rejects paths
starting with `'../'`.

## The bug
```python
# BUG: only rejects './' — misses '../'
return not path.startswith('./')

# Fix:
return not path.startswith('.')
```

## Failing tests (3/7 fail initially)
```
test_parent_relative    ← FAILS ('../components/Button' → bug True as bare)
test_parent_utils       ← FAILS ('../utils' → bug True)
test_grandparent_relative ← FAILS ('../../shared' → bug True)
```
