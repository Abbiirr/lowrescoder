def get_watched_extensions(config):
    """Return set of file extensions to watch from config."""
    raw = config.get('watch_extensions', [])
    # BUG: doesn't strip leading dot — extensions stored as 'py' but checked as '.py'
    return set(raw)
