"""Tests for circular import bug between models and validators."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_can_import_models():
    """Importing models should not raise ImportError.

    Bug: circular import between models.py and validators.py causes
    ImportError at import time.
    """
    try:
        from models import User
    except ImportError as e:
        raise AssertionError(
            f"Circular import error when importing models: {e}"
        ) from e


def test_can_import_validators():
    """Importing validators should not raise ImportError."""
    try:
        from validators import validate_email, validate_age
    except ImportError as e:
        raise AssertionError(
            f"Circular import error when importing validators: {e}"
        ) from e


def test_user_creation():
    """User should be creatable after fixing circular import."""
    from models import User
    u = User("Alice", "alice@example.com", 30)
    assert u.name == "Alice"
    assert u.email == "alice@example.com"
    assert u.age == 30


def test_user_validation():
    """User validation should work correctly."""
    from models import User
    valid_user = User("Alice", "alice@example.com", 30)
    assert valid_user.is_valid() is True

    invalid_user = User("", "not-an-email", 200)
    assert invalid_user.is_valid() is False


def test_validate_email_directly():
    """validate_email should work independently."""
    from validators import validate_email
    assert validate_email("test@example.com") is True
    assert validate_email("bad") is False
    assert validate_email("") is False


def test_validate_age_directly():
    """validate_age should work independently."""
    from validators import validate_age
    assert validate_age(25) is True
    assert validate_age(-1) is False
    assert validate_age(200) is False


def test_user_to_dict():
    """User serialization should work."""
    from models import User
    u = User("Bob", "bob@test.com", 25)
    d = u.to_dict()
    assert d == {"name": "Bob", "email": "bob@test.com", "age": 25}


def test_validate_user_dict():
    """validate_user_dict should validate dict data."""
    from validators import validate_user_dict
    assert validate_user_dict({"name": "Alice", "email": "a@b.com", "age": 30}) is True
    assert validate_user_dict({"name": "", "email": "a@b.com", "age": 30}) is False
    assert validate_user_dict({}) is False
