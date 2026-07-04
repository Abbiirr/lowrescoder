"""Release tag sorter — inspired by go-gitea/gitea release listing."""


def sort_releases(tags):
    """Sort release tags newest-first by semantic version.

    Tags are in the form 'vMAJOR.MINOR.PATCH'.
    """
    # BUG: lexicographic sort — "v1.9.0" sorts after "v1.10.0" incorrectly
    return sorted(tags, reverse=True)
