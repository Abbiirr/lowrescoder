def get_top_contributors(commits, n):
    """Return the top N contributors by commit count, highest first."""
    counts = {}
    for commit in commits:
        author = commit.get('author', '')
        counts[author] = counts.get(author, 0) + 1
    # BUG: sorts ascending (lowest first), so 'top N' picks least active authors
    ranked = sorted(counts.items(), key=lambda x: x[1])
    return [author for author, _ in ranked[:n]]
