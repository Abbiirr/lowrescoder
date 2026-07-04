"""File utilities using os.path — to be migrated to pathlib.Path."""
import os


def list_text_files(directory: str) -> list[str]:
    """Return sorted list of .txt filenames (not full paths) in directory."""
    result = []
    for name in os.listdir(directory):
        full = os.path.join(directory, name)
        if os.path.isfile(full) and name.endswith(".txt"):
            result.append(name)
    return sorted(result)


def read_if_exists(path: str) -> str | None:
    """Return file contents as str, or None if file does not exist."""
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def ensure_dir(path: str) -> str:
    """Create directory (and parents) if it doesn't exist. Return path."""
    if not os.path.isdir(path):
        os.makedirs(path)
    return path
