def get_next_task(tasks):
    """Return the highest-priority pending task (lowest priority_number = highest priority)."""
    pending = [t for t in tasks if t.get('status') == 'pending']
    if not pending:
        return None
    # BUG: returns max priority_number (lowest priority) instead of min
    return max(pending, key=lambda t: t.get('priority', 0))
