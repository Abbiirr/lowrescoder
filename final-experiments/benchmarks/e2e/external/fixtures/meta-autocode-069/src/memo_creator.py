def create_memo(content, visibility=None):
    """Create a memo dict; default visibility should be 'private'."""
    return {
        'content': content,
        # BUG: defaults to 'public' — new memos should be private by default
        'visibility': visibility or 'public',
    }
