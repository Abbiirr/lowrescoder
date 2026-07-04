def is_pinned(memo):
    """Return True if the memo is pinned."""
    # BUG: checks 'pinned' field — correct field is 'is_pinned'
    return memo.get('pinned', False)
