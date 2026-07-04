def count_words(content):
    """Count words in memo content."""
    if not content.strip():
        return 0
    # BUG: split(' ') only splits on single space — tabs and consecutive spaces not handled
    return len(content.split(' '))
