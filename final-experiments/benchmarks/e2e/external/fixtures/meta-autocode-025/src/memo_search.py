"""Memo content search — inspired by usememos/memos search feature."""


def search_memo(content, query):
    """Return True if content contains query (case-insensitive)."""
    if not query:
        return True
    # BUG: case-sensitive comparison misses mixed-case matches
    return query in content
