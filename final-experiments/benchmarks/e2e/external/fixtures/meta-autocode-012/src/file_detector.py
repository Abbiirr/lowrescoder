# File language detector — has a bug.
# This file exists to be fixed by the agent.

LANG_MAP = {
    "py": "python",
    "js": "javascript",
    "ts": "typescript",
    "json": "json",
    "md": "markdown",
    "rs": "rust",
    "go": "go",
    "sh": "shell",
}


def detect_language(filename: str) -> str:
    """Return the language name for a filename, or 'text' if unknown.

    Bug: filename.split('.')[1] retrieves the *second* dot-segment, not the
    last extension. For multi-dot filenames like 'config.test.json' it returns
    'test' instead of 'json'. Single-dot names happen to work by accident.

    Fix: use filename.split('.')[-1] (or rsplit('.', 1)[-1]) to get the last
    segment after the final dot.
    """
    if "." not in filename:
        return "text"
    # BUG: should be split('.')[-1] — [1] takes second segment, not last
    ext = filename.split(".")[1].lower()
    return LANG_MAP.get(ext, "text")
