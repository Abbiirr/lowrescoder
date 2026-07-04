# TASK-213: Fix get_status_label Case-Sensitive Lookup (uptime-kuma pattern)

## Source
Inspired by louislam/uptime-kuma status display. Uppercase status strings
from upstream return None instead of the correct label.

## Goal
Fix `src/status_label.py` so `get_status_label()` handles uppercase status
strings by normalizing to lowercase before lookup.

## The bug
```python
# BUG: case-sensitive dict lookup
return _STATUS_MAP.get(status)

# Fix:
return _STATUS_MAP.get(status.lower())
```

## Failing tests (3/7 fail initially)
```
test_up_upper      ← FAILS ('UP' → bug:None, correct:'Online')
test_down_upper    ← FAILS ('DOWN' → bug:None, correct:'Offline')
test_pending_upper ← FAILS ('PENDING' → bug:None, correct:'Checking')
```
