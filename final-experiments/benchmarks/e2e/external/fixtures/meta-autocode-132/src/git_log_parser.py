def parse_commit_line(line):
    """Parse 'hash|author|message' format into a dict."""
    # BUG: splits on first '|' only, so author+message become one field
    parts = line.split('|', 1)
    if len(parts) < 2:
        return None
    return {
        'hash': parts[0].strip(),
        'author': parts[1].strip(),
        'message': '',
    }
