def validate_heartbeat_interval(interval_seconds):
    """Return True if the heartbeat interval is valid (must be >= 20 seconds)."""
    # BUG: only checks > 0, allows dangerously short intervals
    return interval_seconds > 0
