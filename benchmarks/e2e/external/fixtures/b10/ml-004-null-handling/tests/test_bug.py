"""Tests for null handling bug in data pipeline."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import clean_records, average_field, count_by_field


def test_removes_none_values():
    """Records with None values should be removed."""
    records = [
        {"name": "Alice", "score": 95},
        {"name": "Bob", "score": None},
        {"name": "Charlie", "score": 85},
    ]
    result = clean_records(records)
    assert len(result) == 2
    assert all(r["score"] is not None for r in result)


def test_keeps_zero_values():
    """Records with 0 values should NOT be removed.

    This is the core bug: `if not value` treats 0 as falsy.
    """
    records = [
        {"name": "Alice", "score": 95},
        {"name": "Bob", "score": 0},
        {"name": "Charlie", "score": 85},
    ]
    result = clean_records(records)
    assert len(result) == 3, (
        f"Expected 3 records (0 is valid), got {len(result)}"
    )
    names = [r["name"] for r in result]
    assert "Bob" in names, "Bob with score=0 should not be filtered out"


def test_keeps_empty_string():
    """Records with empty string values should NOT be removed."""
    records = [
        {"name": "Alice", "note": "good"},
        {"name": "Bob", "note": ""},
        {"name": "Charlie", "note": "ok"},
    ]
    result = clean_records(records)
    assert len(result) == 3, (
        f"Expected 3 records (empty string is valid), got {len(result)}"
    )


def test_keeps_false_boolean():
    """Records with False values should NOT be removed."""
    records = [
        {"name": "Alice", "active": True},
        {"name": "Bob", "active": False},
    ]
    result = clean_records(records)
    assert len(result) == 2, (
        f"Expected 2 records (False is valid), got {len(result)}"
    )


def test_average_field_with_zeros():
    """Average should include 0 values, not skip them."""
    records = [
        {"name": "A", "score": 10},
        {"name": "B", "score": 0},
        {"name": "C", "score": 20},
    ]
    result = average_field(records, "score")
    # (10 + 0 + 20) / 3 = 10.0
    assert result == 10.0, f"Expected 10.0 (including zeros), got {result}"


def test_count_by_field_with_zeros():
    """Count should include records with zero values."""
    records = [
        {"name": "A", "category": "x"},
        {"name": "B", "category": "x"},
        {"name": "C", "category": "y"},
        {"name": "D", "score": 0, "category": "y"},
    ]
    result = count_by_field(records, "category")
    assert result == {"x": 2, "y": 2}
