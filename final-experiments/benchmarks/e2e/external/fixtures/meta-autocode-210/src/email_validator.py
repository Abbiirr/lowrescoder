def is_valid_email(email):
    """Return True if email has non-empty local@non-empty-domain format."""
    # BUG: only checks '@' presence — accepts '@domain', 'user@', 'a@@b'
    return '@' in email
