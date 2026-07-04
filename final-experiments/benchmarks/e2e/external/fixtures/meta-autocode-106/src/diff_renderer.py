def render_diff_line(line, line_type):
    """Prefix diff lines with +/- or space."""
    # BUG: 'context' lines should use ' ' (space) prefix, not empty string
    if line_type == 'added':
        return '+' + line
    elif line_type == 'removed':
        return '-' + line
    else:
        return line  # BUG: should be ' ' + line
