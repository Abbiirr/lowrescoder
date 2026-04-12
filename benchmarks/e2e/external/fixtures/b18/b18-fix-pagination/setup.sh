#!/usr/bin/env bash
set -euo pipefail

mkdir -p project

cat > project/paginator.py << 'PYEOF'
"""Paginator module — splits data into pages for API responses."""


class Paginator:
    """Paginate a list of items.

    Args:
        items: The full list of items to paginate.
        page_size: Number of items per page (default 10).
    """

    def __init__(self, items, page_size=10):
        self.items = list(items)
        self.page_size = page_size

    def total_pages(self):
        """Return the total number of pages.

        Returns:
            int: Number of pages needed to display all items.
        """
        if not self.items:
            return 0
        # BUG: integer division then +1 always adds an extra page,
        # even when items divide evenly into page_size
        return len(self.items) // self.page_size + 1

    def get_page(self, page_num):
        """Return items for the given page number (1-indexed).

        Args:
            page_num: Page number (1-indexed).

        Returns:
            list: Items on that page.

        Raises:
            ValueError: If page_num is out of range.
        """
        if page_num < 1 or page_num > self.total_pages():
            raise ValueError(f"Page {page_num} out of range (1-{self.total_pages()})")
        start = (page_num - 1) * self.page_size
        end = start + self.page_size
        return self.items[start:end]

    def has_next(self, page_num):
        """Check if there is a next page."""
        return page_num < self.total_pages()

    def has_prev(self, page_num):
        """Check if there is a previous page."""
        return page_num > 1

    def page_info(self, page_num):
        """Return metadata for a page.

        Returns:
            dict: Page metadata including page number, total pages, etc.
        """
        return {
            "page": page_num,
            "page_size": self.page_size,
            "total_pages": self.total_pages(),
            "total_items": len(self.items),
            "has_next": self.has_next(page_num),
            "has_prev": self.has_prev(page_num),
        }
PYEOF

cat > project/test_paginator.py << 'PYEOF'
"""Tests for the paginator module."""
import unittest
from paginator import Paginator


class TestPaginatorBasic(unittest.TestCase):

    def test_total_pages_exact_division(self):
        """20 items / 10 per page = 2 pages, not 3."""
        p = Paginator(list(range(20)), page_size=10)
        self.assertEqual(p.total_pages(), 2)

    def test_total_pages_with_remainder(self):
        """25 items / 10 per page = 3 pages."""
        p = Paginator(list(range(25)), page_size=10)
        self.assertEqual(p.total_pages(), 3)

    def test_total_pages_single_page(self):
        """5 items / 10 per page = 1 page."""
        p = Paginator(list(range(5)), page_size=10)
        self.assertEqual(p.total_pages(), 1)

    def test_total_pages_empty(self):
        """0 items = 0 pages."""
        p = Paginator([], page_size=10)
        self.assertEqual(p.total_pages(), 0)

    def test_last_page_not_empty(self):
        """The last page must contain items."""
        p = Paginator(list(range(20)), page_size=10)
        last_page = p.get_page(p.total_pages())
        self.assertTrue(len(last_page) > 0, "Last page should not be empty")

    def test_last_page_with_remainder(self):
        """Last page of 25 items should have 5 items."""
        p = Paginator(list(range(25)), page_size=10)
        last_page = p.get_page(p.total_pages())
        self.assertEqual(len(last_page), 5)


class TestPaginatorGetPage(unittest.TestCase):

    def test_first_page(self):
        p = Paginator(list(range(25)), page_size=10)
        self.assertEqual(p.get_page(1), list(range(10)))

    def test_middle_page(self):
        p = Paginator(list(range(25)), page_size=10)
        self.assertEqual(p.get_page(2), list(range(10, 20)))

    def test_last_page(self):
        p = Paginator(list(range(25)), page_size=10)
        self.assertEqual(p.get_page(3), list(range(20, 25)))

    def test_invalid_page_zero(self):
        p = Paginator(list(range(25)), page_size=10)
        with self.assertRaises(ValueError):
            p.get_page(0)

    def test_invalid_page_too_high(self):
        p = Paginator(list(range(25)), page_size=10)
        with self.assertRaises(ValueError):
            p.get_page(4)

    def test_all_items_covered(self):
        """All items should appear exactly once across all pages."""
        items = list(range(25))
        p = Paginator(items, page_size=10)
        all_paged = []
        for i in range(1, p.total_pages() + 1):
            all_paged.extend(p.get_page(i))
        self.assertEqual(all_paged, items)


class TestPaginatorNavigation(unittest.TestCase):

    def test_has_next(self):
        p = Paginator(list(range(25)), page_size=10)
        self.assertTrue(p.has_next(1))
        self.assertTrue(p.has_next(2))
        self.assertFalse(p.has_next(3))

    def test_has_prev(self):
        p = Paginator(list(range(25)), page_size=10)
        self.assertFalse(p.has_prev(1))
        self.assertTrue(p.has_prev(2))

    def test_page_info(self):
        p = Paginator(list(range(25)), page_size=10)
        info = p.page_info(1)
        self.assertEqual(info["total_pages"], 3)
        self.assertEqual(info["total_items"], 25)


if __name__ == "__main__":
    unittest.main()
PYEOF

echo "Setup complete. paginator.py has off-by-one in total_pages()."
