def filter_notifications(notifications, unread_only=False):
    """Filter notification list; optionally return only unread ones."""
    if unread_only:
        # BUG: filters for READ notifications instead of unread
        return [n for n in notifications if n.get('read', False)]
    return notifications
