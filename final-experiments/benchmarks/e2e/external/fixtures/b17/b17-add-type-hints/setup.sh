#!/usr/bin/env bash
# Setup for b17-add-type-hints
# Creates 3 Python files with untyped public functions.
set -euo pipefail

pip install --quiet mypy 2>/dev/null || true

# data_processor.py — no type hints
cat > data_processor.py << 'PYTHON'
"""Data processing functions."""


def filter_by_threshold(data, threshold):
    """Filter a list of numbers, keeping only those above the threshold."""
    return [x for x in data if x > threshold]


def group_by_key(items, key_name):
    """Group a list of dicts by the value of a specific key."""
    groups = {}
    for item in items:
        k = item.get(key_name)
        if k not in groups:
            groups[k] = []
        groups[k].append(item)
    return groups


def compute_stats(numbers):
    """Compute mean, min, max, and count for a list of numbers."""
    if not numbers:
        return {"mean": 0.0, "min": 0.0, "max": 0.0, "count": 0}
    return {
        "mean": sum(numbers) / len(numbers),
        "min": min(numbers),
        "max": max(numbers),
        "count": len(numbers),
    }


def flatten(nested_list):
    """Flatten a list of lists into a single list."""
    result = []
    for sublist in nested_list:
        result.extend(sublist)
    return result


def deduplicate(items):
    """Remove duplicates from a list, preserving order."""
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result
PYTHON

# text_utils.py — no type hints
cat > text_utils.py << 'PYTHON'
"""Text utility functions."""
import re


def word_count(text):
    """Count the number of words in a string."""
    if not text or not text.strip():
        return 0
    return len(text.split())


def reverse_words(text):
    """Reverse the order of words in a string."""
    return " ".join(text.split()[::-1])


def extract_emails(text):
    """Extract all email addresses from a string."""
    pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    return re.findall(pattern, text)


def pad_string(text, width, char=" "):
    """Pad a string to a given width with a character."""
    if len(text) >= width:
        return text
    padding = (width - len(text)) // 2
    result = char * padding + text + char * padding
    if len(result) < width:
        result += char
    return result


def is_palindrome(text):
    """Check if a string is a palindrome (ignoring case and spaces)."""
    cleaned = re.sub(r'[^a-zA-Z0-9]', '', text.lower())
    return cleaned == cleaned[::-1]
PYTHON

# math_helpers.py — no type hints
cat > math_helpers.py << 'PYTHON'
"""Math helper functions."""


def clamp(value, min_val, max_val):
    """Clamp a value between min and max."""
    return max(min_val, min(value, max_val))


def lerp(a, b, t):
    """Linear interpolation between a and b by factor t."""
    return a + (b - a) * t


def factorial(n):
    """Compute factorial of n."""
    if n < 0:
        raise ValueError("Factorial not defined for negative numbers")
    if n <= 1:
        return 1
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result


def fibonacci(n):
    """Return the first n Fibonacci numbers."""
    if n <= 0:
        return []
    if n == 1:
        return [0]
    fib = [0, 1]
    for _ in range(2, n):
        fib.append(fib[-1] + fib[-2])
    return fib


def is_prime(n):
    """Check if n is a prime number."""
    if n < 2:
        return False
    if n < 4:
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False
    i = 5
    while i * i <= n:
        if n % i == 0 or n % (i + 2) == 0:
            return False
        i += 6
    return True
PYTHON

# mypy configuration
cat > mypy.ini << 'INI'
[mypy]
python_version = 3.11
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = True
check_untyped_defs = True
INI

# Tests
cat > test_all.py << 'PYTHON'
"""Tests for all modules."""
import pytest
from data_processor import filter_by_threshold, group_by_key, compute_stats, flatten, deduplicate
from text_utils import word_count, reverse_words, extract_emails, pad_string, is_palindrome
from math_helpers import clamp, lerp, factorial, fibonacci, is_prime


class TestDataProcessor:
    def test_filter_by_threshold(self):
        assert filter_by_threshold([1, 5, 3, 8, 2], 4) == [5, 8]

    def test_group_by_key(self):
        items = [{"type": "a", "v": 1}, {"type": "b", "v": 2}, {"type": "a", "v": 3}]
        groups = group_by_key(items, "type")
        assert len(groups["a"]) == 2
        assert len(groups["b"]) == 1

    def test_compute_stats(self):
        stats = compute_stats([1, 2, 3, 4, 5])
        assert stats["mean"] == 3.0
        assert stats["min"] == 1
        assert stats["max"] == 5
        assert stats["count"] == 5

    def test_compute_stats_empty(self):
        stats = compute_stats([])
        assert stats["count"] == 0

    def test_flatten(self):
        assert flatten([[1, 2], [3, 4], [5]]) == [1, 2, 3, 4, 5]

    def test_deduplicate(self):
        assert deduplicate([1, 2, 2, 3, 1, 4]) == [1, 2, 3, 4]


class TestTextUtils:
    def test_word_count(self):
        assert word_count("hello world") == 2
        assert word_count("") == 0
        assert word_count(None) == 0

    def test_reverse_words(self):
        assert reverse_words("hello world") == "world hello"

    def test_extract_emails(self):
        text = "Contact us at info@example.com or support@test.org"
        emails = extract_emails(text)
        assert "info@example.com" in emails
        assert "support@test.org" in emails

    def test_pad_string(self):
        result = pad_string("hi", 10)
        assert len(result) == 10

    def test_is_palindrome(self):
        assert is_palindrome("racecar") is True
        assert is_palindrome("hello") is False
        assert is_palindrome("A man a plan a canal Panama") is True


class TestMathHelpers:
    def test_clamp(self):
        assert clamp(5, 0, 10) == 5
        assert clamp(-1, 0, 10) == 0
        assert clamp(15, 0, 10) == 10

    def test_lerp(self):
        assert lerp(0, 10, 0.5) == 5.0
        assert lerp(0, 10, 0.0) == 0.0
        assert lerp(0, 10, 1.0) == 10.0

    def test_factorial(self):
        assert factorial(0) == 1
        assert factorial(5) == 120
        with pytest.raises(ValueError):
            factorial(-1)

    def test_fibonacci(self):
        assert fibonacci(5) == [0, 1, 1, 2, 3]
        assert fibonacci(0) == []
        assert fibonacci(1) == [0]

    def test_is_prime(self):
        assert is_prime(2) is True
        assert is_prime(7) is True
        assert is_prime(4) is False
        assert is_prime(1) is False
PYTHON

echo "Setup complete. 3 untyped Python files with mypy config created."
