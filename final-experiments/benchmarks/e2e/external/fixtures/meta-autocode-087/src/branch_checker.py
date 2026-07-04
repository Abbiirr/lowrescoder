import re

def is_valid_branch_name(name):
    """Return True if name is a valid git branch name."""
    if not name:
        return False
    # BUG: allows double-dots (..) which git forbids
    invalid_patterns = [
        r'[\s~^:?*\[\\\x00-\x1f\x7f]',  # spaces, special chars
        r'^/',   # leading slash
        r'/$',   # trailing slash
        r'\.lock$',  # .lock suffix
    ]
    for pattern in invalid_patterns:
        if re.search(pattern, name):
            return False
    return True
