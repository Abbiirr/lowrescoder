# TASK-133: Fix Status Aggregator Up/Down Count (louislam/uptime-kuma pattern)

## Source
Inspired by uptime-kuma status aggregation. Counts 'down' checks instead
of 'up' checks when computing uptime percentage.

## Goal
Fix `src/status_aggregator.py` so `compute_uptime_percent()` counts checks
with status == 'up', not 'down'.

## The bug
```python
# BUG: counts 'down' instead of 'up'
up_count = sum(1 for c in checks if c.get('status') == 'down')

# Fix:
up_count = sum(1 for c in checks if c.get('status') == 'up')
```

## Failing tests (3/7 fail initially)
```
test_all_up     ← FAILS (returns 0.0 instead of 100.0)
test_all_down   ← FAILS (returns 100.0 instead of 0.0)
test_mostly_up  ← FAILS (returns 25.0 instead of 75.0)
```
