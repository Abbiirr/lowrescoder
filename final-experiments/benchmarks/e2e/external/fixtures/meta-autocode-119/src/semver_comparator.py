def compare_versions(v1, v2):
    """Return 1 if v1 > v2, -1 if v1 < v2, 0 if equal."""
    # BUG: compares as strings, not integers
    parts1 = v1.split('.')
    parts2 = v2.split('.')
    for p1, p2 in zip(parts1, parts2):
        if p1 > p2:
            return 1
        elif p1 < p2:
            return -1
    if len(parts1) > len(parts2):
        return 1
    elif len(parts1) < len(parts2):
        return -1
    return 0
