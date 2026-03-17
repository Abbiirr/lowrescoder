"""Minimal path module for py shim."""
class Path:
    """Minimal path class."""
    def __init__(self, value=None):
        self.value = value

    def __str__(self):
        return str(self.value) if self.value else ""

    def __repr__(self):
        return f"Path({self.value!r})"
