def deduplicate_events(events):
    """Remove duplicate events by (type, resource_id) pair."""
    seen = set()
    result = []
    for event in events:
        # BUG: deduplicates by type only, ignores resource_id
        key = event.get('type')
        if key not in seen:
            seen.add(key)
            result.append(event)
    return result
