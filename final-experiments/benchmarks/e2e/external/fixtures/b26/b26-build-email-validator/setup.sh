#!/usr/bin/env bash
set -euo pipefail

mkdir -p project

cat > project/spec.md << 'EOF'
# Email Validation Specification

## Format Rules
1. Must contain exactly one `@` symbol
2. Local part (before @) must be 1-64 characters
3. Domain part (after @) must be 1-255 characters
4. Domain must contain at least one `.`
5. Domain parts must be 1-63 characters each
6. Local part may contain: letters, digits, `.`, `_`, `-`, `+`
7. Local part must not start or end with `.`
8. Domain must only contain: letters, digits, `-`, `.`
9. Domain must not start or end with `-` or `.`

## Normalization
- Convert entire email to lowercase
- Remove any leading/trailing whitespace

## Disposable Domain Check
- Reject emails from domains listed in `disposable_domains.txt`
- Return reason: "disposable domain"

## Return Format
```python
{
    "valid": True/False,
    "reason": "ok" | "missing @" | "invalid local part" | ...,
    "normalized": "user@example.com" | None
}
```
EOF

cat > project/disposable_domains.txt << 'EOF'
mailinator.com
tempmail.com
throwaway.email
guerrillamail.com
yopmail.com
10minutemail.com
trashmail.com
fakeinbox.com
sharklasers.com
guerrillamailblock.com
EOF

cat > project/validator.py << 'PYEOF'
"""Email validation library — implement validate_email() per spec."""
import os
import re


def load_disposable_domains():
    """Load disposable domain list from file."""
    path = os.path.join(os.path.dirname(__file__), "disposable_domains.txt")
    if os.path.exists(path):
        with open(path) as f:
            return set(line.strip().lower() for line in f if line.strip())
    return set()


DISPOSABLE_DOMAINS = load_disposable_domains()


def validate_email(email):
    """Validate an email address per the specification.

    Args:
        email: The email address string to validate.

    Returns:
        dict with keys: valid (bool), reason (str), normalized (str or None)
    """
    # TODO: Implement email validation per spec.md
    # 1. Normalize (lowercase, strip whitespace)
    # 2. Check format rules
    # 3. Check disposable domains
    # 4. Return result dict
    pass
PYEOF

cat > project/test_validator.py << 'PYEOF'
"""Tests for the email validator."""
import unittest
from validator import validate_email


class TestValidEmails(unittest.TestCase):

    def test_simple_valid(self):
        r = validate_email("user@example.com")
        self.assertTrue(r["valid"])
        self.assertEqual(r["reason"], "ok")
        self.assertEqual(r["normalized"], "user@example.com")

    def test_with_plus(self):
        r = validate_email("user+tag@example.com")
        self.assertTrue(r["valid"])

    def test_with_dots(self):
        r = validate_email("first.last@example.com")
        self.assertTrue(r["valid"])

    def test_uppercase_normalized(self):
        r = validate_email("USER@EXAMPLE.COM")
        self.assertTrue(r["valid"])
        self.assertEqual(r["normalized"], "user@example.com")

    def test_whitespace_trimmed(self):
        r = validate_email("  user@example.com  ")
        self.assertTrue(r["valid"])
        self.assertEqual(r["normalized"], "user@example.com")

    def test_subdomain(self):
        r = validate_email("user@mail.example.co.uk")
        self.assertTrue(r["valid"])


class TestInvalidEmails(unittest.TestCase):

    def test_no_at(self):
        r = validate_email("userexample.com")
        self.assertFalse(r["valid"])

    def test_multiple_at(self):
        r = validate_email("user@@example.com")
        self.assertFalse(r["valid"])

    def test_no_domain_dot(self):
        r = validate_email("user@examplecom")
        self.assertFalse(r["valid"])

    def test_local_starts_with_dot(self):
        r = validate_email(".user@example.com")
        self.assertFalse(r["valid"])

    def test_local_ends_with_dot(self):
        r = validate_email("user.@example.com")
        self.assertFalse(r["valid"])

    def test_domain_starts_with_dash(self):
        r = validate_email("user@-example.com")
        self.assertFalse(r["valid"])

    def test_empty_local(self):
        r = validate_email("@example.com")
        self.assertFalse(r["valid"])

    def test_empty_string(self):
        r = validate_email("")
        self.assertFalse(r["valid"])

    def test_local_too_long(self):
        r = validate_email("a" * 65 + "@example.com")
        self.assertFalse(r["valid"])

    def test_invalid_char_in_local(self):
        r = validate_email("user name@example.com")
        self.assertFalse(r["valid"])


class TestDisposableDomains(unittest.TestCase):

    def test_mailinator(self):
        r = validate_email("test@mailinator.com")
        self.assertFalse(r["valid"])
        self.assertIn("disposable", r["reason"].lower())

    def test_tempmail(self):
        r = validate_email("test@tempmail.com")
        self.assertFalse(r["valid"])

    def test_yopmail(self):
        r = validate_email("test@yopmail.com")
        self.assertFalse(r["valid"])


class TestReturnFormat(unittest.TestCase):

    def test_valid_has_all_keys(self):
        r = validate_email("user@example.com")
        self.assertIn("valid", r)
        self.assertIn("reason", r)
        self.assertIn("normalized", r)

    def test_invalid_normalized_is_none(self):
        r = validate_email("bad")
        self.assertIsNone(r["normalized"])


if __name__ == "__main__":
    unittest.main()
PYEOF

echo "Setup complete. validator.py needs validate_email() implemented per spec."
