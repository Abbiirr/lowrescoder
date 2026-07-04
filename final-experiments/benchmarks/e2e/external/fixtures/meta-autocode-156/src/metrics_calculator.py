def calculate_percentage(part, total):
    """Return part as a float percentage of total (e.g. 1/3 → 33.333...)."""
    # BUG: integer division truncates fractional results
    return (part * 100) // total
