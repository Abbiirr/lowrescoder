# TASK-231: Fix format_uptime_percent Divides Total/Up Instead of Up/Total (uptime-kuma pattern)

## Source
Inspired by louislam/uptime-kuma uptime calculation. Swapped numerator/denominator
gives 100%+ values for anything less than full uptime.

## Goal
Fix `src/uptime_percent.py` so `format_uptime_percent()` divides `seconds_up`
by `seconds_total`.

## The bug
```python
# BUG: inverted division
return round(seconds_total / seconds_up * 100, 1)

# Fix:
return round(seconds_up / seconds_total * 100, 1)
```

## Failing tests (3/7 fail initially)
```
test_80_percent ← FAILS (80/100 → bug:125.0, correct:80.0)
test_90_percent ← FAILS (9/10 → bug:111.1, correct:90.0)
test_50_percent ← FAILS (1/2 → bug:200.0, correct:50.0)
```
