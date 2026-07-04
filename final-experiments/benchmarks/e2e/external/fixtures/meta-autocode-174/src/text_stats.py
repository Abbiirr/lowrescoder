def count_words(text):
    """Count the number of words in text."""
    # BUG: splits on literal space only — empty strings from consecutive
    # spaces inflate the count; tabs and other whitespace are not split
    return len(text.split(' '))
