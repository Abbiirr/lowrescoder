def summarize_memo(content, max_words=5):
    """Return the first max_words words of content joined by spaces."""
    words = content.split()
    # BUG: off-by-one — slices to max_words-1 instead of max_words
    return ' '.join(words[:max_words - 1])
