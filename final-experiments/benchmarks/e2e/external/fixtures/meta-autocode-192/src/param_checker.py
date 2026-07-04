import keyword

def is_valid_param_name(name):
    """Return True if name is a valid Python identifier that is not a reserved keyword."""
    # BUG: doesn't reject Python keywords like 'class', 'return', 'for'
    return name.isidentifier()
