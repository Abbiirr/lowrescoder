def expand_tabs(line, tab_width):
    """Expand tab characters in a line to spaces using the given tab width."""
    # BUG: ignores tab_width, always uses 4 spaces
    return line.replace('\t', '    ')
