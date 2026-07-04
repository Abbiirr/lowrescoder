import re

def camel_to_snake(name):
    """Convert camelCase or PascalCase to snake_case."""
    # BUG: produces leading underscore for PascalCase ('MyClass' → '_my_class')
    return re.sub(r'([A-Z])', r'_\1', name).lower()
