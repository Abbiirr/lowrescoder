def format_line_number(line_num, total_lines):
    """Right-justify line_num to the width needed for total_lines."""
    # BUG: always uses width 4 — wrong for files with fewer than 1000 lines
    width = 4
    return str(line_num).rjust(width)
