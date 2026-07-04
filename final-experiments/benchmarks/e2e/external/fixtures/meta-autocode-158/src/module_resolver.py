def is_relative_path(path):
    """Return True if path is a relative import (starts with ./ or ../)."""
    # BUG: only checks './' — parent directory paths '../' return False
    return path.startswith('./')
