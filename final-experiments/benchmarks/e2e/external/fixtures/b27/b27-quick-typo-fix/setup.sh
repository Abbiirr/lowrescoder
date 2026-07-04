#!/usr/bin/env bash
# Setup for b27-quick-typo-fix
set -euo pipefail

cat > api.py << 'PY'
"""Pricing API module."""


def _apply_discount(price: float, discount: float) -> float:
    """Apply a percentage discount to a price."""
    return price * (1 - discount / 100)


def calcualte_total(items: list[dict]) -> float:
    """Calculate the total price for a list of items.

    Each item dict has 'price' (float), 'quantity' (int),
    and optional 'discount' (float, percentage).
    """
    total = 0.0
    for item in items:
        price = item["price"]
        quantity = item["quantity"]
        discount = item.get("discount", 0)
        discounted = _apply_discount(price, discount)
        total += discounted * quantity
    return round(total, 2)
PY

cat > test_api.py << 'PY'
"""Tests for pricing API."""
import unittest
from api import calculate_total


class TestCalculateTotal(unittest.TestCase):
    def test_single_item_no_discount(self):
        items = [{"price": 10.0, "quantity": 2}]
        self.assertEqual(calculate_total(items), 20.0)

    def test_single_item_with_discount(self):
        items = [{"price": 100.0, "quantity": 1, "discount": 10}]
        self.assertEqual(calculate_total(items), 90.0)

    def test_multiple_items(self):
        items = [
            {"price": 25.0, "quantity": 2},
            {"price": 50.0, "quantity": 1, "discount": 20},
        ]
        # 25*2 + 50*0.8 = 50 + 40 = 90
        self.assertEqual(calculate_total(items), 90.0)

    def test_empty_list(self):
        self.assertEqual(calculate_total([]), 0.0)

    def test_rounding(self):
        items = [{"price": 10.0, "quantity": 3, "discount": 15}]
        # 10 * 0.85 * 3 = 25.5
        self.assertEqual(calculate_total(items), 25.5)


if __name__ == "__main__":
    unittest.main()
PY

echo "Setup complete. api.py has a typo in function name (calcualte_total)."
