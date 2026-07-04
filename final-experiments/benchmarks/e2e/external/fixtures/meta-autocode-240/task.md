# TASK-240: Fix format_response_time Divides by 100 Not 1000 (uptime-kuma pattern)

## Source
Inspired by louislam/uptime-kuma response time display. Dividing by 100
instead of 1000 makes 1000ms display as '10.00s' instead of '1.00s'.

## Goal
Fix `src/response_time.py` so `format_response_time()` divides by 1000
when converting to seconds.

## The bug
```python
# BUG: wrong divisor
return f'{ms / 100:.2f}s'

# Fix:
return f'{ms / 1000:.2f}s'
```

## Failing tests (3/7 fail initially)
```
test_1000ms ← FAILS (1000ms → bug:'10.00s', correct:'1.00s')
test_2500ms ← FAILS (2500ms → bug:'25.00s', correct:'2.50s')
test_1234ms ← FAILS (1234ms → bug:'12.34s', correct:'1.23s')
```
