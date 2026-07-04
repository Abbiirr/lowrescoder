def strip_leading_zeros(s):
    """Remove leading zeros from a numeric string, keeping at least one digit."""
    # BUG: lstrip('0') returns '' for all-zero strings like '000'
    return s.lstrip('0')
