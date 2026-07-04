def normalize_line_endings(text):
    """Normalize all line endings (\\r\\n and standalone \\r) to \\n."""
    # BUG: only replaces \r\n, leaves standalone \r (old Mac CR) unchanged
    return text.replace('\r\n', '\n')
