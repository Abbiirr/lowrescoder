def highlight_matches(text, query):
    """Wrap all occurrences of query in text with <mark> tags (case-insensitive)."""
    # BUG: case-sensitive replacement — misses matches that differ in case
    return text.replace(query, f'<mark>{query}</mark>')
