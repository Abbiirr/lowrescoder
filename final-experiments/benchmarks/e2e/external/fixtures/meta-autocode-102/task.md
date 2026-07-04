# TASK-102: Fix Webhook Event Dispatch Logic (go-gitea/gitea pattern)

## Source
Inspired by go-gitea/gitea webhook dispatching. The event must match the
subscribed list — the extra `or bool(subscribed_events)` makes every event
dispatch when ANY subscription exists.

## Goal
Fix `src/webhook_dispatcher.py` so `should_dispatch_event()` only returns
True when `event_type in subscribed_events`.

## The bug
```python
# BUG: extra 'or' clause fires for any non-empty subscribed list
return event_type in subscribed_events or bool(subscribed_events)

# Fix: simple membership test
return event_type in subscribed_events
```

## Failing tests (3/7 fail initially)
```
test_non_matching_event_not_dispatched ← FAILS (True != False)
test_unsubscribed_event_blocked        ← FAILS (True != False)
test_wrong_event_type_blocked          ← FAILS (True != False)
```
