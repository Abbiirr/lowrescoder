"""Wiki page name sanitizer — inspired by go-gitea/gitea wiki."""


def sanitize_wiki_name(name: str) -> str:
    """Convert a wiki page title to a valid filename.

    Spaces are replaced with underscores. Leading/trailing whitespace is
    stripped and consecutive spaces collapse to a single underscore.

    Args:
        name: raw wiki page title

    Returns:
        sanitized filename-safe string
    """
    # BUG: replaces each space character individually — consecutive spaces
    # produce multiple consecutive underscores instead of one.
    return name.replace(" ", "_")
