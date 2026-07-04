# TASK-123: Fix Event Scheduler Due Check (jesseduffield/lazygit pattern)

## Source
Inspired by lazygit scheduled event dispatching. Uses `>=` (future events)
instead of `<=` (past/current events) when filtering due events.

## Goal
Fix `src/event_scheduler.py` so `get_due_events()` returns events whose
`scheduled_at` is at or before `current_time`.

## The bug
```python
# BUG: >= returns future events, not past ones
if event['scheduled_at'] >= current_time:

# Fix:
if event['scheduled_at'] <= current_time:
```

## Failing tests (3/7 fail initially)
```
test_past_event_is_due  ← FAILS (past event not in result)
test_future_event_not_due ← FAILS (future event incorrectly included)
test_mixed_events       ← FAILS (wrong set returned)
```
