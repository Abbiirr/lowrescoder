def merge_tag_sets(set_a, set_b):
    """Return union of two tag sets (all tags from either set)."""
    # BUG: returns intersection instead of union
    return set_a & set_b
