def format_duration(seconds):
    """Format a duration in seconds as 'Xh Ym Zs'."""
    h = seconds // 3600
    # BUG: calculates total minutes instead of remainder minutes
    m = seconds // 60
    s = seconds % 60
    return f'{h}h {m}m {s}s'
