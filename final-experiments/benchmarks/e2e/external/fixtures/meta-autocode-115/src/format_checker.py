import re

def is_valid_email(email):
    """Return True if email has basic valid format."""
    # BUG: pattern requires TLD of exactly 2 chars, misses .com, .org, .io etc.
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2}$'
    return bool(re.match(pattern, email))
