def is_printable_ascii(text):
    """Return True if all characters are printable ASCII (32-126 inclusive)."""
    # BUG: missing lower-bound check — allows control characters (ord 0-31)
    return all(ord(c) < 127 for c in text)
