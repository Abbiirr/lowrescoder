def calculate_uptime_percentage(checks):
    """Return uptime % from list of check dicts with 'status': 'up'|'down'."""
    if not checks:
        return 0.0
    # BUG: counts total instead of 'up' checks in numerator
    up_count = len(checks)
    total = len(checks)
    return round(up_count / total * 100, 2)
