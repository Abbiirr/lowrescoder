def branch_from_ref(ref):
    """Return the branch name from a full git ref string."""
    # BUG: split('/')[-1] only returns the last path segment —
    # nested branch names like 'feature/my-branch' are truncated
    return ref.split('/')[-1]
