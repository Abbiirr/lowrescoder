# TASK-033: Fix Response Time Average Excluding Failures (louislam/uptime-kuma pattern)

## Source
Inspired by louislam/uptime-kuma monitor response time tracking. When a
monitor check fails, uptime-kuma records 0 ms response time. The average
displayed to users should exclude these failed pings to show true latency.
The bug includes zeros, dragging the average down artificially.

## Goal
Fix `src/response_time.py` so `calculate_avg_response_time()` filters out
zero entries before averaging.

## The bug
```python
# BUG: includes zero (failed) entries
return sum(response_times) / len(response_times)

# Fix: exclude zeros
valid = [t for t in response_times if t > 0]
if not valid:
    return 0
return sum(valid) / len(valid)
```

## Failing tests (3/7 fail initially)
```
test_zeros_excluded_from_avg  ← FAILS ([100,200,0] → 100 not 150)
test_heavy_failures           ← FAILS ([0,0,0,100] → 25 not 100)
test_mixed_zeros_and_values   ← FAILS ([50,0,150] → ~66.7 not 100)
```
