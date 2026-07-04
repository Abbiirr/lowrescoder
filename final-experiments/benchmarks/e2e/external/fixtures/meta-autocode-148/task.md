# TASK-148: Fix Severity Filter Threshold (off-by-one — >= vs >)

## Source
Inspired by uptime-kuma incident filtering logic. The severity threshold check
uses strict greater-than `>` instead of inclusive `>=`, silently dropping
incidents that are exactly at the threshold boundary.

## Goal
Fix `src/incident_resolver.py` so `filter_high_severity()` includes issues
with severity **equal to** the threshold.

## The bug
```python
# BUG: excludes severity == threshold
return [i for i in issues if i.get('severity', 0) > threshold]

# Fix: inclusive threshold
return [i for i in issues if i.get('severity', 0) >= threshold]
```

## Failing tests (3/7 fail initially)
```
test_exactly_at_threshold  ← FAILS ([] instead of [issue])
test_threshold_zero        ← FAILS ([] instead of [issue])
test_boundary_case         ← FAILS ([] instead of [id=2])
```
