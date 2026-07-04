def count_vowels(text):
    """Count the number of vowels (a, e, i, o, u) in text."""
    # BUG: starts at index 1 — skips the first character
    return sum(1 for c in text[1:] if c.lower() in 'aeiou')
