def number_lines(lines, start=1):
    """Return list of (line_number, line) tuples."""
    result = []
    # BUG: starts at 0 instead of using start parameter
    for i, line in enumerate(lines):
        result.append((i, line))
    return result
