#!/usr/bin/env bash
set -euo pipefail

mkdir -p project

cat > project/search.py << 'PYEOF'
"""Search module — finds matching items in a list."""


def normalize(text):
    """Normalize text for comparison."""
    # BUG: .encode('ascii') crashes on non-ASCII input
    return text.encode('ascii').decode('ascii').lower().strip()


def search(query, items):
    """Return items that contain the query string (case-insensitive).

    Args:
        query: Search string.
        items: List of strings to search through.

    Returns:
        List of matching items.
    """
    normalized_query = normalize(query)
    results = []
    for item in items:
        if normalized_query in normalize(item):
            results.append(item)
    return results


def search_exact(query, items):
    """Return items that exactly match the query (case-insensitive).

    Args:
        query: Search string.
        items: List of strings to search through.

    Returns:
        List of exactly matching items.
    """
    normalized_query = normalize(query)
    return [item for item in items if normalize(item) == normalized_query]
PYEOF

cat > project/test_search.py << 'PYEOF'
"""Tests for the search module."""
import unittest
from search import search, search_exact


class TestSearchASCII(unittest.TestCase):
    """Tests with ASCII input — these should already pass."""

    def test_basic_search(self):
        items = ["apple", "banana", "cherry"]
        self.assertEqual(search("app", items), ["apple"])

    def test_case_insensitive(self):
        items = ["Apple", "BANANA", "cherry"]
        self.assertEqual(search("apple", items), ["Apple"])

    def test_no_match(self):
        items = ["apple", "banana"]
        self.assertEqual(search("xyz", items), [])

    def test_empty_query(self):
        items = ["apple", "banana"]
        self.assertEqual(search("", items), ["apple", "banana"])


class TestSearchUnicode(unittest.TestCase):
    """Tests with Unicode input — these currently crash."""

    def test_accented_characters(self):
        items = ["Caf\u00e9 Latte", "Green Tea", "Cr\u00e8me Br\u00fbl\u00e9e"]
        result = search("caf\u00e9", items)
        self.assertIn("Caf\u00e9 Latte", result)

    def test_cjk_characters(self):
        items = ["\u6771\u4eac\u30bf\u30ef\u30fc", "\u5bcc\u58eb\u5c71", "\u65b0\u5bbf\u99c5"]
        result = search("\u5bcc\u58eb", items)
        self.assertIn("\u5bcc\u58eb\u5c71", result)

    def test_emoji_in_search(self):
        items = ["\ud83c\udf4e Apple", "\ud83c\udf4c Banana", "\ud83c\udf52 Cherry"]
        result = search("\ud83c\udf4e", items)
        self.assertIn("\ud83c\udf4e Apple", result)

    def test_mixed_unicode_ascii(self):
        items = ["na\u00efve", "resume", "r\u00e9sum\u00e9"]
        result = search("na\u00efve", items)
        self.assertIn("na\u00efve", result)

    def test_cyrillic(self):
        items = ["\u041c\u043e\u0441\u043a\u0432\u0430", "\u041f\u0440\u0430\u0433\u0430", "\u0411\u0435\u0440\u043b\u0438\u043d"]
        result = search("\u043c\u043e\u0441\u043a\u0432\u0430", items)
        self.assertIn("\u041c\u043e\u0441\u043a\u0432\u0430", result)

    def test_exact_unicode(self):
        items = ["Caf\u00e9", "cafe", "CAFE"]
        result = search_exact("caf\u00e9", items)
        self.assertIn("Caf\u00e9", result)


if __name__ == "__main__":
    unittest.main()
PYEOF

echo "Setup complete. search.py crashes on any non-ASCII input."
