ALLOWED_TYPES = ['feat', 'fix', 'docs', 'style', 'refactor', 'test', 'chore']

def lint_commit_message(message):
    """Return list of lint errors for conventional commit format."""
    errors = []
    if not message:
        errors.append('message is empty')
        return errors
    parts = message.split(':', 1)
    if len(parts) < 2:
        errors.append('missing colon separator')
        return errors
    commit_type = parts[0].strip()
    # BUG: checks if type is NOT in ALLOWED_TYPES, but appends error for allowed types
    if commit_type in ALLOWED_TYPES:
        errors.append(f'unknown commit type: {commit_type}')
    return errors
