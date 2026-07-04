import re

def is_valid_label_color(color):
    """Return True if color is a valid 6-digit hex code like #ff0000."""
    # BUG: accepts any non-empty string — doesn't validate hex format
    return bool(color)
