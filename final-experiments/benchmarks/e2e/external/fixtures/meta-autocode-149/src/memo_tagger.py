def find_memos_by_tag(memos, tag):
    """Return memos containing the given tag (case-insensitive match)."""
    # BUG: case-sensitive — misses memos with differently-cased tag
    return [m for m in memos if tag in m.get('tags', [])]
