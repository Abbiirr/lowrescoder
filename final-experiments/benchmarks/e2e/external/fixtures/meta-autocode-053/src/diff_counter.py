def count_diff_lines(diff_text):
    """Count added and removed lines in a unified diff, excluding file headers."""
    added = 0
    removed = 0
    for line in diff_text.split('\n'):
        # BUG: '+++' / '---' header lines are counted as added/removed
        if line.startswith('+'):
            added += 1
        elif line.startswith('-'):
            removed += 1
    return {'added': added, 'removed': removed}
