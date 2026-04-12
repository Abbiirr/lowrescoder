#!/usr/bin/env bash
# Setup for b17-rename-module
# Creates a 5-file Python project where utils.py is imported everywhere.
set -euo pipefail

# utils.py — the module to be renamed
cat > utils.py << 'PYTHON'
"""Utility functions used throughout the project."""
import re
from datetime import datetime


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    return text.strip('-')


def format_date(dt: datetime) -> str:
    """Format a datetime as ISO date string."""
    return dt.strftime("%Y-%m-%d")


def truncate(text: str, max_length: int = 100) -> str:
    """Truncate text to max_length, adding ellipsis if needed."""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def validate_email(email: str) -> bool:
    """Basic email validation."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def deep_merge(base: dict, override: dict) -> dict:
    """Deep merge two dictionaries."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result
PYTHON

# models.py — imports from utils
cat > models.py << 'PYTHON'
"""Data models."""
from utils import slugify, validate_email


class User:
    def __init__(self, name: str, email: str):
        if not validate_email(email):
            raise ValueError(f"Invalid email: {email}")
        self.name = name
        self.email = email
        self.slug = slugify(name)

    def __repr__(self):
        return f"User(name={self.name!r}, email={self.email!r})"


class Article:
    def __init__(self, title: str, body: str):
        self.title = title
        self.body = body
        self.slug = slugify(title)

    def __repr__(self):
        return f"Article(title={self.title!r})"
PYTHON

# services.py — imports from utils
cat > services.py << 'PYTHON'
"""Service layer."""
from utils import format_date, truncate, deep_merge
from datetime import datetime


class NotificationService:
    def __init__(self):
        self.notifications = []

    def send(self, message: str, timestamp: datetime = None):
        ts = timestamp or datetime.now()
        self.notifications.append({
            "message": truncate(message, 200),
            "date": format_date(ts),
        })
        return True

    def get_all(self):
        return self.notifications


class ConfigService:
    def __init__(self, defaults: dict):
        self.config = defaults

    def update(self, overrides: dict):
        self.config = deep_merge(self.config, overrides)
        return self.config

    def get(self, key: str, default=None):
        return self.config.get(key, default)
PYTHON

# api.py — imports from utils
cat > api.py << 'PYTHON'
"""API layer."""
from utils import validate_email, slugify, truncate
from models import User


def create_user(name: str, email: str) -> dict:
    """Create a user and return their data."""
    if not validate_email(email):
        return {"error": "Invalid email"}
    user = User(name=name, email=email)
    return {
        "name": user.name,
        "email": user.email,
        "slug": user.slug,
    }


def preview_article(title: str, body: str) -> dict:
    """Return a preview of an article."""
    return {
        "title": title,
        "slug": slugify(title),
        "preview": truncate(body, 150),
    }
PYTHON

# app.py — imports from utils
cat > app.py << 'PYTHON'
"""Main application."""
from utils import slugify, format_date, validate_email
from models import User, Article
from services import NotificationService
from datetime import datetime


def run():
    """Run the application."""
    # Create a user
    user = User("John Doe", "john@example.com")
    print(f"Created user: {user}")
    print(f"  Slug: {slugify(user.name)}")

    # Create an article
    article = Article("Hello World!", "This is the first post.")
    print(f"Created article: {article}")

    # Send notification
    ns = NotificationService()
    ns.send(f"New article: {article.title}", datetime(2025, 1, 15))
    print(f"Notifications: {ns.get_all()}")

    # Validate email
    print(f"Valid email: {validate_email('test@example.com')}")
    print(f"Invalid email: {validate_email('not-an-email')}")

    return True


if __name__ == "__main__":
    run()
PYTHON

# test_app.py — imports from utils
cat > test_app.py << 'PYTHON'
"""Tests for the application."""
import pytest
from utils import slugify, format_date, truncate, validate_email, deep_merge
from models import User, Article
from services import NotificationService, ConfigService
from api import create_user, preview_article
from datetime import datetime


class TestUtils:
    def test_slugify(self):
        assert slugify("Hello World!") == "hello-world"
        assert slugify("  Spaces  ") == "spaces"
        assert slugify("CamelCase") == "camelcase"

    def test_format_date(self):
        dt = datetime(2025, 3, 15)
        assert format_date(dt) == "2025-03-15"

    def test_truncate(self):
        assert truncate("short", 100) == "short"
        assert truncate("a" * 200, 100) == "a" * 97 + "..."

    def test_validate_email(self):
        assert validate_email("user@example.com") is True
        assert validate_email("invalid") is False
        assert validate_email("") is False

    def test_deep_merge(self):
        base = {"a": 1, "b": {"c": 2, "d": 3}}
        override = {"b": {"c": 99}, "e": 5}
        result = deep_merge(base, override)
        assert result == {"a": 1, "b": {"c": 99, "d": 3}, "e": 5}


class TestModels:
    def test_user_creation(self):
        user = User("Alice", "alice@example.com")
        assert user.slug == "alice"

    def test_user_invalid_email(self):
        with pytest.raises(ValueError):
            User("Bob", "not-email")

    def test_article_creation(self):
        article = Article("My Post!", "Content here")
        assert article.slug == "my-post"


class TestServices:
    def test_notification_service(self):
        ns = NotificationService()
        ns.send("Hello", datetime(2025, 1, 1))
        assert len(ns.get_all()) == 1
        assert ns.get_all()[0]["date"] == "2025-01-01"

    def test_config_service(self):
        cs = ConfigService({"debug": False, "db": {"host": "localhost"}})
        cs.update({"db": {"port": 5432}})
        assert cs.get("db") == {"host": "localhost", "port": 5432}


class TestAPI:
    def test_create_user(self):
        result = create_user("Alice", "alice@example.com")
        assert result["slug"] == "alice"
        assert "error" not in result

    def test_create_user_invalid_email(self):
        result = create_user("Bob", "invalid")
        assert "error" in result

    def test_preview_article(self):
        result = preview_article("Test", "Body content")
        assert result["slug"] == "test"
        assert result["preview"] == "Body content"
PYTHON

echo "Setup complete. 5-file project with utils.py imported everywhere."
