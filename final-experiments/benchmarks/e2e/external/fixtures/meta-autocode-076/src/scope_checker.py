def has_required_scopes(token_scopes, required_scopes):
    """Return True if token_scopes contains ALL of required_scopes."""
    # BUG: checks any overlap (intersection) instead of full containment
    return bool(set(token_scopes) & set(required_scopes))
