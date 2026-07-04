# TASK-119: Fix Semantic Version Comparator (vitejs/vite pattern)

## Source
Inspired by vitejs/vite dependency version comparison. Comparing version
strings lexicographically instead of numerically causes '10' < '9'.

## Goal
Fix `src/semver_comparator.py` so `compare_versions()` compares version
parts as integers.

## The bug
```python
# BUG: string comparison — '10' < '9' lexicographically
if p1 > p2:

# Fix: integer comparison
if int(p1) > int(p2):
```

## Failing tests (3/7 fail initially)
```
test_minor_multidigit  ← FAILS (1.10.0 vs 1.9.0)
test_patch_multidigit  ← FAILS (2.0.10 vs 2.0.9)
test_major_multidigit  ← FAILS (10.0.0 vs 9.0.0)
```
