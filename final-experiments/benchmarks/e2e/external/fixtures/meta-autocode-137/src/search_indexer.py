def build_index(documents):
    """Build inverted index: word → list of doc_ids containing that word."""
    index = {}
    for doc in documents:
        doc_id = doc['id']
        words = doc.get('content', '').lower().split()
        for word in words:
            # BUG: overwrites index[word] instead of appending
            index[word] = [doc_id]
    return index
