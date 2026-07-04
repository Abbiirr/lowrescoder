def format_uptime_percent(seconds_up, seconds_total):
    """Return uptime percentage rounded to 1 decimal place."""
    if seconds_total == 0:
        return 0.0
    # BUG: divides total by up instead of up by total
    return round(seconds_total / seconds_up * 100, 1)
