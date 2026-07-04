def remove_extension(filename):
    """Return filename without its extension (last dot segment)."""
    # BUG: split('.')[0] removes everything after the FIRST dot
    # — multi-dot names like 'app.test.js' become 'app' instead of 'app.test'
    return filename.split('.')[0]
