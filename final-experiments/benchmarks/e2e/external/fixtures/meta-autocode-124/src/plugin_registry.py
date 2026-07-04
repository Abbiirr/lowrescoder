_registry = {}

def register_plugin(name, handler):
    """Register a plugin handler by name."""
    _registry[name] = handler

def get_plugin(name):
    """Look up a plugin by name (case-insensitive)."""
    # BUG: case-sensitive lookup — 'MyPlugin' != 'myplugin'
    return _registry.get(name)

def clear_registry():
    _registry.clear()
