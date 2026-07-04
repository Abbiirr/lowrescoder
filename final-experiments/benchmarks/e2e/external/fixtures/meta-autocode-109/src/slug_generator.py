import re

def generate_slug(title):
    """Generate URL-safe slug from title."""
    slug = title.lower()
    # BUG: replaces spaces with underscore instead of hyphen
    slug = re.sub(r'\s+', '_', slug)
    slug = re.sub(r'[^a-z0-9_]', '', slug)
    return slug
