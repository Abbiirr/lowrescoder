def find_matching_labels(issue_labels, filter_labels):
    """Return labels from issue_labels that match any in filter_labels (case-insensitive)."""
    # BUG: case-sensitive comparison
    return [l for l in issue_labels if l in filter_labels]
