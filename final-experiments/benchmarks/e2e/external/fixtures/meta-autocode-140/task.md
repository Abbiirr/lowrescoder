# TASK-140: Fix Alert Throttler Time Unit (louislam/uptime-kuma pattern)

## Source
Inspired by uptime-kuma alert cooldown logic. Compares elapsed time in
seconds against cooldown in minutes (60× unit mismatch), sending alerts
far too early.

## Goal
Fix `src/alert_throttler.py` so `should_send_alert()` converts cooldown
to seconds before comparing.

## The bug
```python
# BUG: cooldown_minutes compared to elapsed seconds directly
return elapsed >= cooldown_minutes

# Fix: convert to seconds
return elapsed >= cooldown_minutes * 60
```

## Failing tests (3/7 fail initially)
```
test_four_minutes_not_ready  ← FAILS (240s >= 5min incorrectly True)
test_one_minute_too_early    ← FAILS (60s >= 2min incorrectly True)
test_half_cooldown_elapsed   ← FAILS (150s >= 5min incorrectly True)
```
