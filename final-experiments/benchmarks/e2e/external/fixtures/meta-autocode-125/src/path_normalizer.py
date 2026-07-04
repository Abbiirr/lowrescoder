import re

def normalize_path(path):
    """Normalize a file path: convert backslashes, collapse multiple slashes,
    strip trailing slash."""
    # BUG: only collapses multiple forward slashes, doesn't convert backslashes
    path = re.sub(r'/+', '/', path)
    path = path.rstrip('/')
    return path
