def get_recent_events(events, n):
    """Return the N most recent events (last N in chronological order)."""
    if n <= 0:
        return []
    # BUG: returns first N events instead of last N
    return events[:n]
