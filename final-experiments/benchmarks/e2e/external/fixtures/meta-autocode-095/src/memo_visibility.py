VISIBILITY_LEVELS = ['private', 'protected', 'public']

def can_view_memo(memo, viewer_role):
    """Return True if viewer_role can see the memo based on its visibility."""
    visibility = memo.get('visibility', 'private')
    # BUG: 'protected' memos should be visible to 'member' and 'admin',
    # but bug allows 'public' viewers too
    if visibility == 'public':
        return True
    if visibility == 'protected':
        # BUG: should check viewer_role in ('member', 'admin')
        return viewer_role in ('member', 'admin', 'public')
    # private: only admin
    return viewer_role == 'admin'
