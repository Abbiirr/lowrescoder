def max_line_length(lines):
    """Return the length of the longest line in the list."""
    # BUG: slices off the last line — misses it when computing the max
    return max((len(line) for line in lines[:-1]), default=0)
