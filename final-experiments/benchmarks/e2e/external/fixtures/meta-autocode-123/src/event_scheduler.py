def get_due_events(events, current_time):
    """Return events whose scheduled_at <= current_time (due now or overdue)."""
    due = []
    for event in events:
        # BUG: uses >= instead of <=, returns future events instead of past
        if event['scheduled_at'] >= current_time:
            due.append(event)
    return due
