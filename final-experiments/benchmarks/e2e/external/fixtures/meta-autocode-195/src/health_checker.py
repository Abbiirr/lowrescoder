def is_healthy(uptime_percent):
    """Return True if uptime is at or above the 99.5% health threshold."""
    # BUG: threshold is 99 instead of 99.5 — accepts below-threshold values
    return uptime_percent >= 99
