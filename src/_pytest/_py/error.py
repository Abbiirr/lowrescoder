"""Minimal error module for py shim."""
class Error:
    """Minimal error class."""
    def __init__(self, value=None):
        self.value = value
    
    def str__(self):
        return str(self.value) if self.value else ""
