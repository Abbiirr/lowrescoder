def get_page_items(items, page, page_size):
    """Return items for the given 1-indexed page number."""
    # BUG: uses page instead of page-1, skipping first page's items
    offset = page * page_size
    return items[offset:offset + page_size]
