def count_lines(text):
    """Return the number of lines in text."""
    # BUG: adds extra phantom line when text ends with newline (or is empty)
    return text.count('\n') + 1
