# Pagination utility — has a bug.
# This file exists to be fixed by the agent.

def paginate(items, page, per_page):
    """Return one page of items.

    Args:
        items: sequence to paginate
        page: 1-indexed page number
        per_page: number of items per page

    Returns:
        list slice for the requested page

    Current bug: page offset is calculated as page*per_page instead of
    (page-1)*per_page, so page 1 returns items starting at index per_page
    instead of index 0.
    """
    start = page * per_page          # BUG: should be (page - 1) * per_page
    end = start + per_page
    return list(items[start:end])


def total_pages(total_items, per_page):
    """Return total number of pages needed."""
    if per_page <= 0:
        raise ValueError("per_page must be positive")
    return (total_items + per_page - 1) // per_page
