def get_memo_author(memo):
    """Return the username of the memo author."""
    # BUG: reads 'creator' key instead of 'author'
    creator = memo.get('creator', {})
    return creator.get('username')
