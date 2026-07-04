import re

def extract_tags(content):
    """Extract hashtag names from memo content."""
    # BUG: pattern doesn't allow hyphens in tag names
    matches = re.findall(r'#([a-zA-Z0-9_]+)', content)
    return list(dict.fromkeys(matches))  # deduplicate, preserve order
