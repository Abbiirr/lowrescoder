import math

def page_count(total_items, page_size):
    """Return the total number of pages needed to display all items."""
    # BUG: integer division truncates — partial last page not counted
    return total_items // page_size
