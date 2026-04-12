#!/usr/bin/env bash
# Setup for b15-add-csv-export
# Creates a report module that returns data but has no export function.
set -euo pipefail

# Report module — no export capability
cat > report.py << 'PYTHON'
"""Report data generation module."""
from datetime import date


def get_monthly_report(year: int, month: int) -> list:
    """Generate monthly sales report data.

    Returns a list of dicts with keys:
        date, product, quantity, unit_price, total
    """
    data = [
        {"date": f"{year}-{month:02d}-01", "product": "Widget A", "quantity": 150, "unit_price": 9.99, "total": 1498.50},
        {"date": f"{year}-{month:02d}-03", "product": "Widget B", "quantity": 75, "unit_price": 19.99, "total": 1499.25},
        {"date": f"{year}-{month:02d}-05", "product": "Gadget X", "quantity": 200, "unit_price": 4.50, "total": 900.00},
        {"date": f"{year}-{month:02d}-08", "product": "Widget A", "quantity": 120, "unit_price": 9.99, "total": 1198.80},
        {"date": f"{year}-{month:02d}-10", "product": "Gadget Y", "quantity": 50, "unit_price": 29.99, "total": 1499.50},
        {"date": f"{year}-{month:02d}-12", "product": "Widget B", "quantity": 90, "unit_price": 19.99, "total": 1799.10},
        {"date": f"{year}-{month:02d}-15", "product": "Gadget X", "quantity": 180, "unit_price": 4.50, "total": 810.00},
        {"date": f"{year}-{month:02d}-18", "product": "Widget A", "quantity": 200, "unit_price": 9.99, "total": 1998.00},
        {"date": f"{year}-{month:02d}-20", "product": "Gadget Y", "quantity": 65, "unit_price": 29.99, "total": 1949.35},
        {"date": f"{year}-{month:02d}-25", "product": "Widget B", "quantity": 110, "unit_price": 19.99, "total": 2198.90},
    ]
    return data


def get_report_summary(data: list) -> dict:
    """Summarize report data."""
    total_quantity = sum(row["quantity"] for row in data)
    total_revenue = sum(row["total"] for row in data)
    unique_products = len(set(row["product"] for row in data))
    return {
        "total_quantity": total_quantity,
        "total_revenue": round(total_revenue, 2),
        "unique_products": unique_products,
        "row_count": len(data),
    }
PYTHON

# Tests for existing functionality
cat > test_report.py << 'PYTHON'
"""Tests for report module."""
import pytest
from report import get_monthly_report, get_report_summary


def test_monthly_report_returns_list():
    data = get_monthly_report(2025, 1)
    assert isinstance(data, list)
    assert len(data) == 10


def test_monthly_report_has_correct_keys():
    data = get_monthly_report(2025, 1)
    expected_keys = {"date", "product", "quantity", "unit_price", "total"}
    for row in data:
        assert set(row.keys()) == expected_keys


def test_report_summary():
    data = get_monthly_report(2025, 1)
    summary = get_report_summary(data)
    assert summary["row_count"] == 10
    assert summary["unique_products"] == 4
    assert summary["total_quantity"] == 1240
    assert summary["total_revenue"] == 15351.40
PYTHON

echo "Setup complete. Report module created without export capability."
