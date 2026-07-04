def get_extension(path):
    """Return the file extension without dot, or '' if the file has no extension."""
    # BUG: returns full filename/basename when there's no dot — rsplit returns original
    return path.rsplit('.', 1)[-1]
