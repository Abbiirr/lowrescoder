def list_themes(themes):
    """Return themes sorted alphabetically (case-insensitive)."""
    # BUG: case-sensitive sort — uppercase letters sort before lowercase
    # 'Zenburn' (Z=90) appears before 'abyss' (a=97)
    return sorted(themes)
