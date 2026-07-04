def paginate(items, page, per_page):
    """Return a page of items with pagination metadata."""
    start = (page - 1) * per_page
    end = start + per_page
    page_items = items[start:end]
    return {
        'items': page_items,
        # BUG: returns count of this page's items instead of total collection size
        'total': len(page_items),
        'page': page,
        'per_page': per_page,
    }
