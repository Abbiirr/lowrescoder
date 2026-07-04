def to_title_case(text):
    """Capitalize the first letter of each word, lowercasing the rest."""
    # BUG: str.title() treats apostrophes as word boundaries, uppercasing after them
    return text.title()
