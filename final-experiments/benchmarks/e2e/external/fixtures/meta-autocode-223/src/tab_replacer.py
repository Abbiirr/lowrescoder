def replace_tabs(text, width=4):
    """Replace each tab character with `width` spaces."""
    # BUG: replaces tab with a single space regardless of width
    return text.replace('\t', ' ')
