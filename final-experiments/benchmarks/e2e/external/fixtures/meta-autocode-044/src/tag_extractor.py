def extract_tags_from_memo(content):
    """Extract all #hashtags from a (possibly multi-line) memo."""
    # BUG: only processes the first line — tags on subsequent lines are missed
    first_line = content.split('\n')[0]
    words = first_line.split()
    return [w[1:] for w in words if w.startswith('#')]
