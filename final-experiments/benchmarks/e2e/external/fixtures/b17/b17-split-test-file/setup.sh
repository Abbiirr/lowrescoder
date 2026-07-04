#!/usr/bin/env bash
# Setup for b17-split-test-file
# Creates a monolithic test_all.py with tests for 3 different modules.
set -euo pipefail

# calculator.py
cat > calculator.py << 'PYTHON'
"""Calculator module with arithmetic operations."""


class Calculator:
    """Simple calculator with memory."""

    def __init__(self):
        self.memory = 0.0

    def add(self, a, b):
        return a + b

    def subtract(self, a, b):
        return a - b

    def multiply(self, a, b):
        return a * b

    def divide(self, a, b):
        if b == 0:
            raise ZeroDivisionError("Cannot divide by zero")
        return a / b

    def store(self, value):
        self.memory = value

    def recall(self):
        return self.memory

    def clear_memory(self):
        self.memory = 0.0
PYTHON

# formatter.py
cat > formatter.py << 'PYTHON'
"""String formatting module."""


def format_currency(amount, symbol="$", decimals=2):
    """Format a number as currency."""
    formatted = f"{amount:,.{decimals}f}"
    return f"{symbol}{formatted}"


def format_percentage(value, decimals=1):
    """Format a number as percentage."""
    return f"{value:.{decimals}f}%"


def format_file_size(bytes_count):
    """Format bytes as human-readable file size."""
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(bytes_count)
    unit_index = 0
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    if unit_index == 0:
        return f"{int(size)} {units[unit_index]}"
    return f"{size:.1f} {units[unit_index]}"


def title_case(text):
    """Convert text to title case, handling common articles."""
    small_words = {"a", "an", "the", "and", "but", "or", "for", "in", "on", "at", "to"}
    words = text.split()
    result = []
    for i, word in enumerate(words):
        if i == 0 or word.lower() not in small_words:
            result.append(word.capitalize())
        else:
            result.append(word.lower())
    return " ".join(result)
PYTHON

# validator.py
cat > validator.py << 'PYTHON'
"""Validation module."""
import re


def validate_email(email):
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_phone(phone):
    """Validate US phone number format."""
    cleaned = re.sub(r'[^\d]', '', phone)
    return len(cleaned) == 10 or (len(cleaned) == 11 and cleaned[0] == '1')


def validate_url(url):
    """Validate URL format."""
    pattern = r'^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/.*)?$'
    return bool(re.match(pattern, url))


def validate_password(password, min_length=8):
    """Validate password strength."""
    if len(password) < min_length:
        return False, "Password too short"
    if not re.search(r'[A-Z]', password):
        return False, "Must contain uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Must contain lowercase letter"
    if not re.search(r'[0-9]', password):
        return False, "Must contain digit"
    return True, "Password is valid"


def validate_username(username, min_length=3, max_length=20):
    """Validate username format."""
    if len(username) < min_length:
        return False, "Username too short"
    if len(username) > max_length:
        return False, "Username too long"
    if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', username):
        return False, "Username must start with letter, only alphanumeric and underscore"
    return True, "Username is valid"
PYTHON

# Monolithic test file — all tests mixed together
cat > test_all.py << 'PYTHON'
"""All tests in one file — should be split into per-module test files."""
import pytest
from calculator import Calculator
from formatter import format_currency, format_percentage, format_file_size, title_case
from validator import validate_email, validate_phone, validate_url, validate_password, validate_username


# ===== Calculator Tests =====

class TestCalculatorArithmetic:
    def test_add(self):
        calc = Calculator()
        assert calc.add(2, 3) == 5
        assert calc.add(-1, 1) == 0
        assert calc.add(0.1, 0.2) == pytest.approx(0.3)

    def test_subtract(self):
        calc = Calculator()
        assert calc.subtract(5, 3) == 2
        assert calc.subtract(1, 5) == -4

    def test_multiply(self):
        calc = Calculator()
        assert calc.multiply(3, 4) == 12
        assert calc.multiply(-2, 3) == -6
        assert calc.multiply(0, 100) == 0

    def test_divide(self):
        calc = Calculator()
        assert calc.divide(10, 2) == 5
        assert calc.divide(7, 2) == 3.5

    def test_divide_by_zero(self):
        calc = Calculator()
        with pytest.raises(ZeroDivisionError):
            calc.divide(1, 0)


class TestCalculatorMemory:
    def test_store_and_recall(self):
        calc = Calculator()
        calc.store(42)
        assert calc.recall() == 42

    def test_clear_memory(self):
        calc = Calculator()
        calc.store(42)
        calc.clear_memory()
        assert calc.recall() == 0.0

    def test_initial_memory_is_zero(self):
        calc = Calculator()
        assert calc.recall() == 0.0


# ===== Formatter Tests =====

class TestFormatCurrency:
    def test_basic_currency(self):
        assert format_currency(1234.56) == "$1,234.56"

    def test_custom_symbol(self):
        assert format_currency(100, symbol="€") == "€100.00"

    def test_no_decimals(self):
        assert format_currency(1000, decimals=0) == "$1,000"

    def test_large_number(self):
        assert format_currency(1000000) == "$1,000,000.00"


class TestFormatPercentage:
    def test_basic_percentage(self):
        assert format_percentage(75.5) == "75.5%"

    def test_integer_percentage(self):
        assert format_percentage(100.0, decimals=0) == "100%"


class TestFormatFileSize:
    def test_bytes(self):
        assert format_file_size(500) == "500 B"

    def test_kilobytes(self):
        assert format_file_size(1024) == "1.0 KB"

    def test_megabytes(self):
        assert format_file_size(1048576) == "1.0 MB"

    def test_gigabytes(self):
        assert format_file_size(1073741824) == "1.0 GB"


class TestTitleCase:
    def test_basic(self):
        assert title_case("the quick brown fox") == "The Quick Brown Fox"

    def test_articles(self):
        assert title_case("a tale of two cities") == "A Tale of Two Cities"


# ===== Validator Tests =====

class TestValidateEmail:
    def test_valid_emails(self):
        assert validate_email("user@example.com") is True
        assert validate_email("first.last@company.org") is True

    def test_invalid_emails(self):
        assert validate_email("invalid") is False
        assert validate_email("@example.com") is False
        assert validate_email("user@") is False
        assert validate_email("") is False


class TestValidatePhone:
    def test_valid_phones(self):
        assert validate_phone("5551234567") is True
        assert validate_phone("(555) 123-4567") is True
        assert validate_phone("1-555-123-4567") is True

    def test_invalid_phones(self):
        assert validate_phone("12345") is False
        assert validate_phone("") is False


class TestValidateUrl:
    def test_valid_urls(self):
        assert validate_url("http://example.com") is True
        assert validate_url("https://www.example.com/path") is True

    def test_invalid_urls(self):
        assert validate_url("ftp://example.com") is False
        assert validate_url("not-a-url") is False


class TestValidatePassword:
    def test_valid_password(self):
        valid, msg = validate_password("SecurePass1")
        assert valid is True

    def test_too_short(self):
        valid, msg = validate_password("Sh0rt")
        assert valid is False
        assert "short" in msg.lower()

    def test_no_uppercase(self):
        valid, msg = validate_password("lowercase1")
        assert valid is False

    def test_no_digit(self):
        valid, msg = validate_password("NoDigitHere")
        assert valid is False


class TestValidateUsername:
    def test_valid_username(self):
        valid, msg = validate_username("alice_123")
        assert valid is True

    def test_too_short(self):
        valid, msg = validate_username("ab")
        assert valid is False

    def test_starts_with_number(self):
        valid, msg = validate_username("123abc")
        assert valid is False

    def test_too_long(self):
        valid, msg = validate_username("a" * 21)
        assert valid is False
PYTHON

echo "Setup complete. Monolithic test_all.py with tests for 3 modules."
