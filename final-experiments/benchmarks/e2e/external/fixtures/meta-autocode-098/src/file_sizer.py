def format_file_size(size_bytes):
    """Format byte count as human-readable string (B, KB, MB, GB)."""
    # BUG: uses 1000 instead of 1024 for binary units
    if size_bytes < 1000:
        return f"{size_bytes} B"
    elif size_bytes < 1000 ** 2:
        return f"{size_bytes / 1000:.1f} KB"
    elif size_bytes < 1000 ** 3:
        return f"{size_bytes / 1000 ** 2:.1f} MB"
    else:
        return f"{size_bytes / 1000 ** 3:.1f} GB"
