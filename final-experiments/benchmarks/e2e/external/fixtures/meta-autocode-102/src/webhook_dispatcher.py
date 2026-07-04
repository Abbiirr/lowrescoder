def should_dispatch_event(event_type, subscribed_events):
    """Return True if event_type should trigger webhook dispatch."""
    # BUG: uses 'or' operator — True if event matches OR if subscribed_events is truthy
    return event_type in subscribed_events or bool(subscribed_events)
