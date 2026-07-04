def sort_tags(tags, by='name'):
    """Sort tags by 'name' or 'count', descending by count, ascending by name."""
    if by == 'count':
        # BUG: sorts ascending by count instead of descending
        return sorted(tags, key=lambda t: t.get('count', 0))
    else:
        return sorted(tags, key=lambda t: t.get('name', ''))
