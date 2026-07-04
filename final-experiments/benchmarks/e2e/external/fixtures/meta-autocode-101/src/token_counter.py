def count_tokens(text):
    """Approximate token count: split on whitespace and punctuation."""
    if not text:
        return 0
    # BUG: counts characters instead of words/tokens
    return len(text)
