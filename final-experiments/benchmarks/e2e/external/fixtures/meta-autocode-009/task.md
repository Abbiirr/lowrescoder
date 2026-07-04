# TASK-009: Fix Incident Tracker EOF Bug (uptime-kuma pattern)

## Source
Inspired by louislam/uptime-kuma heartbeat incident detection.
When a service is still down at the end of the heartbeat stream, the open
incident is silently dropped. This is a classic "handle EOF state" bug.

## Goal
Fix `src/incident_tracker.py` so that an ongoing incident at end-of-stream
is returned with `end=None`.

## The bug
```python
# After the loop, in_incident may still be True — never appended:
for hb in heartbeats:
    if hb["status"] == "down" and not in_incident:
        in_incident = True
        start_ts = hb["ts"]
    elif hb["status"] == "up" and in_incident:
        in_incident = False
        incidents.append({"start": start_ts, "end": hb["ts"]})
# BUG: no post-loop check for open incident

# Fix — add after the loop:
if in_incident:
    incidents.append({"start": start_ts, "end": None})
```

## All 7 tests must pass
```
test_all_up_no_incidents          ← passes
test_resolved_incident            ← passes
test_ongoing_incident_at_end      ← FAILS (returns [])
test_single_down_at_end           ← FAILS (returns [])
test_two_incidents_second_ongoing ← FAILS (returns only 1 incident)
test_empty_stream                 ← passes
test_two_resolved_incidents       ← passes
```
