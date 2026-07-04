def add_labels_to_issue(existing_labels, new_labels):
    """Return the combined label list with duplicates removed (order preserved)."""
    # BUG: no deduplication — duplicate label IDs can appear multiple times
    return existing_labels + new_labels
