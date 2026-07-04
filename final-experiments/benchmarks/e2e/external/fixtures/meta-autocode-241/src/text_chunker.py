def split_into_chunks(text, size):
    """Split text into non-overlapping chunks of at most `size` characters."""
    # BUG: range stops at len(text)-1 — last chunk dropped when len%size==1
    return [text[i:i+size] for i in range(0, len(text) - 1, size)]
