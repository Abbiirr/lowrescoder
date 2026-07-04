"""Data models with validation.

Bug: imports validators at module level, creating a circular import.
models.py imports validators.py, which imports models.py.
Fix: move the import inside the function that needs it (lazy import).
"""
from validators import validate_email, validate_age  # Bug: circular import


class User:
    """User model with validation."""

    def __init__(self, name, email, age):
        self.name = name
        self.email = email
        self.age = age

    def validate(self):
        """Validate user fields. Returns list of error strings."""
        errors = []
        if not self.name or not isinstance(self.name, str):
            errors.append("name must be a non-empty string")
        if not validate_email(self.email):
            errors.append("invalid email")
        if not validate_age(self.age):
            errors.append("age must be between 0 and 150")
        return errors

    def is_valid(self):
        """Return True if the user passes all validations."""
        return len(self.validate()) == 0

    def to_dict(self):
        """Serialize user to dict."""
        return {"name": self.name, "email": self.email, "age": self.age}
