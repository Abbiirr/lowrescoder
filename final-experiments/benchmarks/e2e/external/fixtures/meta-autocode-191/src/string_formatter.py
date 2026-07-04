def left_pad(s, width, char):
    """Pad string s on the left to given width using the specified char."""
    # BUG: always pads with space — ignores the char argument
    return s.rjust(width)
