_HIGHLIGHT_EXTENSIONS = {'.py', '.js', '.ts', '.css', '.html', '.json', '.yaml', '.yml', '.sh', '.rs'}

def should_highlight(filename):
    """Return True if the file type supports syntax highlighting."""
    # BUG: case-sensitive extension check — '.PY', '.JS' etc. not recognised
    ext = ('.' + filename.rsplit('.', 1)[1]) if '.' in filename else ''
    return ext in _HIGHLIGHT_EXTENSIONS
