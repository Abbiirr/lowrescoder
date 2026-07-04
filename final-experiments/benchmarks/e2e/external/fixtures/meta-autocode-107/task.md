# TASK-107: Fix Notification Filter Unread Logic (go-gitea/gitea pattern)

## Source
Inspired by go-gitea/gitea notification filtering. When `unread_only=True`,
the filter should return notifications where `read == False`, not `read == True`.

## Goal
Fix `src/notification_filter.py` so `filter_notifications()` keeps items where
`read` is False (unread).

## The bug
```python
# BUG: keeps read notifications
return [n for n in notifications if n.get('read', False)]

# Fix: keeps unread
return [n for n in notifications if not n.get('read', False)]
```

## Failing tests (3/7 fail initially)
```
test_unread_only_returns_unread  ← FAILS ([{id:2}] doesn't contain ids 1,3)
test_unread_only_excludes_read   ← FAILS (id 2 IS in result)
test_unread_only_count           ← FAILS (1 != 2)
```
