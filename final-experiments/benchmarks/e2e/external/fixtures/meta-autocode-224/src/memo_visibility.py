def is_memo_public(memo):
    """Return True if memo visibility is 'PUBLIC'."""
    # BUG: checks lowercase 'public' — 'PUBLIC' returns False
    return memo.get('visibility') == 'public'
