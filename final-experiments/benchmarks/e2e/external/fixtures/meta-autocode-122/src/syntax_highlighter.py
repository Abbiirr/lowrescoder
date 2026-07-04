def get_highlight_lines(start_line, end_line, highlight_ranges):
    """Return set of line numbers that fall within any highlight range."""
    highlighted = set()
    for (range_start, range_end) in highlight_ranges:
        for line in range(start_line, end_line):
            # BUG: excludes end_line from the view AND uses < instead of <= for range_end
            if range_start <= line < range_end:
                highlighted.add(line)
    return highlighted
