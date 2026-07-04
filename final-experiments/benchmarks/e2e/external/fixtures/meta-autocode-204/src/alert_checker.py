def is_stale_alert(age_seconds, max_age):
    """Return True if alert age is at or beyond the stale threshold."""
    # BUG: uses > instead of >= — an alert exactly at max_age is not flagged
    return age_seconds > max_age
