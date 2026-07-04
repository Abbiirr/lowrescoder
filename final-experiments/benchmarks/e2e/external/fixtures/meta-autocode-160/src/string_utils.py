def is_palindrome(text):
    """Return True if text is a palindrome (alphanumeric only, case-insensitive)."""
    cleaned = ''.join(c for c in text if c.isalnum())
    # BUG: case-sensitive comparison — 'Racecar' fails because 'R' != 'r'
    return cleaned == cleaned[::-1]
