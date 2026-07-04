def can_merge_pr(pr):
    """Return True if PR is mergeable: approved, CI passing, no conflicts."""
    # BUG: checks 'approved' instead of 'review_approved'
    return (
        pr.get('approved', False) and
        pr.get('ci_passing', False) and
        not pr.get('has_conflicts', True)
    )
