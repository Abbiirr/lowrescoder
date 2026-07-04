def get_memo_tags(memo):
    """Return the list of tags from a memo dict."""
    # BUG: wrong key 'tag' instead of 'tags' — always returns default []
    return memo.get('tag', [])
