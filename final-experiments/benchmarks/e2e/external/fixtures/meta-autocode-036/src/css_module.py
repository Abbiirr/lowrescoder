import hashlib

def generate_css_module_class(file_path, class_name):
    """Generate a unique scoped CSS class name for a module."""
    # BUG: hashes only class_name — same class name in different files collides
    hash_val = hashlib.md5(class_name.encode()).hexdigest()[:6]
    return f"{class_name}_{hash_val}"
