def format_commit_date(year, month, day):
    """Return ISO-formatted date string with zero-padded month and day."""
    # BUG: no zero-padding — month 3 becomes '3' not '03'
    return f"{year}-{month}-{day}"
