_TYPES = {'feat', 'fix', 'docs', 'style', 'refactor', 'test', 'chore'}

def is_conventional_commit(message):
    """Return True if message follows conventional commit format (type: description)."""
    if ': ' not in message:
        return False
    type_part = message.split(': ', 1)[0]
    # BUG: case-sensitive — 'Feat', 'FIX' etc. not recognised
    return type_part in _TYPES
