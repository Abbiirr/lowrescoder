def get_page_count(total_items, page_size):
    """Return total number of pages needed."""
    if total_items == 0:
        return 0
    # BUG: integer division floors, missing items in last page
    return total_items // page_size
