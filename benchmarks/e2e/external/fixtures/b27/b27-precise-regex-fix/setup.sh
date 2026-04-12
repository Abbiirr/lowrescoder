#!/usr/bin/env bash
# Setup for b27-precise-regex-fix
set -euo pipefail

cat > validator.py << 'PY'
"""Email validator module."""
import re

# BUG: [a-zA-Z0-9_] doesn't allow dots in the local part
EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9_]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')


def is_valid_email(email: str) -> bool:
    """Check if the given string is a valid email address."""
    if not email or not isinstance(email, str):
        return False
    return bool(EMAIL_PATTERN.match(email))


def validate_email_list(emails: list[str]) -> dict[str, bool]:
    """Validate a list of emails, returning a dict of email -> valid."""
    return {email: is_valid_email(email) for email in emails}
PY

cat > test_validator.py << 'PY'
"""Tests for email validator."""
import unittest
from validator import is_valid_email


class TestEmailValidator(unittest.TestCase):
    """Test email validation regex."""

    def test_simple_email(self):
        self.assertTrue(is_valid_email("alice@example.com"))

    def test_email_with_dots(self):
        """This is the key test — dots in local part must be valid."""
        self.assertTrue(is_valid_email("john.doe@example.com"))

    def test_email_with_multiple_dots(self):
        self.assertTrue(is_valid_email("first.middle.last@company.org"))

    def test_email_with_underscore(self):
        self.assertTrue(is_valid_email("user_name@domain.io"))

    def test_email_with_numbers(self):
        self.assertTrue(is_valid_email("user123@test.co.uk"))

    def test_email_with_dot_and_underscore(self):
        self.assertTrue(is_valid_email("john.doe_jr@example.com"))

    def test_reject_no_at_sign(self):
        self.assertFalse(is_valid_email("invalidemail.com"))

    def test_reject_no_domain(self):
        self.assertFalse(is_valid_email("user@"))

    def test_reject_no_local(self):
        self.assertFalse(is_valid_email("@example.com"))

    def test_reject_spaces(self):
        self.assertFalse(is_valid_email("user @example.com"))

    def test_reject_empty(self):
        self.assertFalse(is_valid_email(""))

    def test_reject_double_at(self):
        self.assertFalse(is_valid_email("user@@example.com"))


if __name__ == "__main__":
    unittest.main()
PY

echo "Setup complete. validator.py regex rejects valid emails with dots."
