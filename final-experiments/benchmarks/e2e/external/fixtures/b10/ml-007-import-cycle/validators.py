"""Validation utilities.

Bug: imports User from models at module level, creating a circular import.
validators.py imports models.py, which imports validators.py.
Fix: move the import inside the function that needs it, or remove it.
"""
import re
from models import User  # Bug: circular import — not even needed here


def validate_email(email):
    """Check that email has a basic valid format."""
    if not isinstance(email, str):
        return False
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def validate_age(age):
    """Check that age is a reasonable integer."""
    if not isinstance(age, (int, float)):
        return False
    return 0 <= age <= 150


def validate_name(name):
    """Check that name is a non-empty string."""
    return isinstance(name, str) and len(name.strip()) > 0


def validate_user_dict(data):
    """Validate a user dict has required fields.

    This function actually needs User, but should use a lazy import.
    """
    required = {"name", "email", "age"}
    if not isinstance(data, dict):
        return False
    if not required.issubset(data.keys()):
        return False
    return validate_name(data["name"]) and validate_email(data["email"]) and validate_age(data["age"])
