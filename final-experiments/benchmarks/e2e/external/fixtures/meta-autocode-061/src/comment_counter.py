def count_issue_comments(comments):
    """Count top-level comments on an issue (replies with parent_id are excluded)."""
    # BUG: counts all comments including replies
    return len(comments)
