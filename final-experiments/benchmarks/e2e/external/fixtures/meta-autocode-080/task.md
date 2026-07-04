# TASK-080: Fix Monitor Last Check Timestamp Update (louislam/uptime-kuma pattern)

## Source
Inspired by louislam/uptime-kuma heartbeat recording. The `last_check`
timestamp must be updated on EVERY heartbeat, not only when the monitor was
previously down. The bug skips the update when the monitor was previously up.

## Goal
Fix `src/monitor_updater.py` so `update_monitor_status()` always sets
`monitor['last_check'] = current_time`.

## The bug
```python
# BUG: only updates when was previously down
if not monitor.get('is_up', True):
    monitor['last_check'] = current_time

# Fix: always update
monitor['last_check'] = current_time
```

## Failing tests (3/7 fail initially)
```
test_up_monitor_last_check_updated  ← FAILS (was up: last_check stays 0, expected 123)
test_up_to_down_updates_last_check  ← FAILS (was up: last_check stays 50, expected 100)
test_repeated_up_checks_update_time ← FAILS (consecutive up checks: last_check stays 10, expected 30)
```
