def compute_uptime_percent(checks):
    """Return percentage of checks where status is 'up'."""
    if not checks:
        return 0.0
    # BUG: counts 'down' instead of 'up'
    up_count = sum(1 for c in checks if c.get('status') == 'down')
    return (up_count / len(checks)) * 100
