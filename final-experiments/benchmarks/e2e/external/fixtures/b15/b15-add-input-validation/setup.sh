#!/usr/bin/env bash
# Setup for b15-add-input-validation
# Creates a form handler that accepts any input without validation.
set -euo pipefail

# Form handler — no validation
cat > forms.py << 'PYTHON'
"""Form handling module for user registration."""


class RegistrationResult:
    """Result of a registration attempt."""

    def __init__(self, success: bool, user_data: dict = None, errors: list = None):
        self.success = success
        self.user_data = user_data or {}
        self.errors = errors or []


def process_registration(data: dict) -> RegistrationResult:
    """Process a user registration form submission.

    Args:
        data: Dictionary with keys 'name', 'email', 'password'

    Returns:
        RegistrationResult with success status and any errors
    """
    # Currently accepts everything without validation
    user = {
        "name": data.get("name", ""),
        "email": data.get("email", ""),
        "password": data.get("password", ""),
    }
    return RegistrationResult(success=True, user_data=user)


def format_user_display(name: str, email: str) -> str:
    """Format user info for display."""
    return f"{name} <{email}>"
PYTHON

# Tests — existing passing tests
cat > test_forms.py << 'PYTHON'
"""Tests for form handling."""
import pytest
from forms import process_registration, format_user_display, RegistrationResult


def test_valid_registration():
    """A valid registration should succeed."""
    data = {
        "name": "Alice Smith",
        "email": "alice@example.com",
        "password": "securepass123",
    }
    result = process_registration(data)
    assert result.success is True
    assert result.user_data["name"] == "Alice Smith"
    assert result.user_data["email"] == "alice@example.com"


def test_format_user_display():
    assert format_user_display("Bob", "bob@test.com") == "Bob <bob@test.com>"


def test_result_has_errors_list():
    result = RegistrationResult(success=False, errors=["test error"])
    assert result.errors == ["test error"]
    assert result.success is False
PYTHON

echo "Setup complete. Form handler with no validation created."
