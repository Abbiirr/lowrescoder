# Commit statistics counter — has a bug.
# This file exists to be fixed by the agent.


def count_commits_by_author(commits: list) -> dict:
    """Count how many commits each author made.

    Args:
        commits: list of dicts with at least an 'author' key

    Returns:
        dict mapping author name to commit count

    Bug: uses assignment (= 1) instead of increment (+= 1).
    Every author's count resets to 1 on each commit, so authors
    with multiple commits always show a count of 1.
    """
    stats = {}
    for commit in commits:
        author = commit["author"]
        if author not in stats:
            stats[author] = 0
        stats[author] = 1  # BUG: should be += 1
    return stats


def top_contributor(commits: list) -> str:
    """Return the author with the most commits."""
    if not commits:
        return ""
    counts = count_commits_by_author(commits)
    return max(counts, key=counts.get)
