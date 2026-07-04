#!/usr/bin/env bash
# Setup for b27-one-line-fix
set -euo pipefail

cat > counter.py << 'PY'
"""Counter module — counts items in a range (inclusive)."""


def count_items(start: int, end: int) -> list[int]:
    """Return a list of integers from start to end, inclusive."""
    result = []
    i = start
    while i < end:  # BUG: should be <=
        result.append(i)
        i += 1
    return result


def total_in_range(start: int, end: int) -> int:
    """Return the sum of integers from start to end, inclusive."""
    return sum(count_items(start, end))
PY

cat > test_counter.py << 'PY'
"""Tests for counter module."""
import unittest
from counter import count_items, total_in_range


class TestCountItems(unittest.TestCase):
    def test_inclusive_range(self):
        """count_items(1, 5) should return [1, 2, 3, 4, 5]."""
        self.assertEqual(count_items(1, 5), [1, 2, 3, 4, 5])

    def test_single_item(self):
        """count_items(3, 3) should return [3]."""
        self.assertEqual(count_items(3, 3), [3])

    def test_total_in_range(self):
        """total_in_range(1, 4) should be 1+2+3+4 = 10."""
        self.assertEqual(total_in_range(1, 4), 10)

    def test_zero_range(self):
        """count_items(0, 0) should return [0]."""
        self.assertEqual(count_items(0, 0), [0])


if __name__ == "__main__":
    unittest.main()
PY

echo "Setup complete. counter.py has an off-by-one error."
