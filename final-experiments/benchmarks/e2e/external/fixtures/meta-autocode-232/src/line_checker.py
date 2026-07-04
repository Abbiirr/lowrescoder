def is_empty_line(line):
    """Return True if line is empty or contains only whitespace."""
    # BUG: only detects the empty string — whitespace-only lines treated as non-empty
    return line == ''
