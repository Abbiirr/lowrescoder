def slugify(text):
    """Convert text to URL slug: lowercase, spaces replaced by hyphens."""
    # BUG: uses underscore '_' instead of hyphen '-'
    return text.lower().replace(' ', '_')
