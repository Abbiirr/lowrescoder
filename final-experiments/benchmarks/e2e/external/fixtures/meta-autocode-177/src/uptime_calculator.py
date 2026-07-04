def uptime_percentage(checks):
    """Return percentage (0-100.0) of status checks that are UP."""
    if not checks:
        return 0.0
    # BUG: case-sensitive comparison — 'up' and 'Up' are not counted
    up_count = sum(1 for c in checks if c == 'UP')
    return (up_count / len(checks)) * 100
