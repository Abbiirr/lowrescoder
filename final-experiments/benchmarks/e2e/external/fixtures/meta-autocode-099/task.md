# TASK-099: Fix Config Merger Base Mutation (vitejs/vite pattern)

## Source
Inspired by vitejs/vite config merging. The merger assigns `result = base`
directly, so all mutations affect the caller's original config.

## Goal
Fix `src/config_merger.py` so `merge_configs()` does not mutate `base`.

## The bug
```python
# BUG: result IS base — mutations go straight through
result = base

# Fix: copy first
import copy
result = copy.deepcopy(base)
```

## Failing tests (3/7 fail initially)
```
test_base_not_mutated          ← FAILS (base['server']['port'] became 8080)
test_base_nested_unchanged     ← FAILS (base['db']['host'] mutated)
test_independent_results       ← FAILS (base['cfg'] mutated on first call)
```
