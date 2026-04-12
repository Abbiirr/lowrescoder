#!/usr/bin/env bash
set -euo pipefail

pip install pytest --quiet

cat > processor.py << 'PY'
"""Data processor with intentionally slow algorithms."""


def custom_sort(items):
    """Sort a list of comparable items in ascending order. Returns a new list."""
    # Bubble sort: O(n^2) - intentionally slow
    result = list(items)
    n = len(result)
    for i in range(n):
        for j in range(0, n - i - 1):
            if result[j] > result[j + 1]:
                result[j], result[j + 1] = result[j + 1], result[j]
    return result


def find_duplicates(items):
    """Find all duplicate values in a list. Returns sorted list of duplicates."""
    # Nested loop: O(n^2) - intentionally slow
    duplicates = []
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            if items[i] == items[j] and items[i] not in duplicates:
                duplicates.append(items[i])
    duplicates.sort()
    return duplicates


def group_by_key(items, key_fn):
    """Group items by key function. Returns dict mapping keys to lists of items.

    Keys appear in the order first encountered. Items within each group
    maintain their original order.
    """
    # Rebuild-per-key approach: O(n*k) where k = unique keys - intentionally slow
    keys_seen = []
    for item in items:
        k = key_fn(item)
        if k not in keys_seen:
            keys_seen.append(k)

    result = {}
    for k in keys_seen:
        result[k] = []
        for item in items:
            if key_fn(item) == k:
                result[k].append(item)
    return result
PY

cat > test_processor.py << 'PY'
import pytest
from processor import custom_sort, find_duplicates, group_by_key


def test_custom_sort_integers():
    assert custom_sort([5, 3, 8, 1, 9, 2]) == [1, 2, 3, 5, 8, 9]


def test_custom_sort_strings():
    assert custom_sort(["banana", "apple", "cherry"]) == ["apple", "banana", "cherry"]


def test_find_duplicates():
    items = [1, 2, 3, 2, 4, 5, 1, 6, 3]
    assert find_duplicates(items) == [1, 2, 3]


def test_find_duplicates_none():
    assert find_duplicates([1, 2, 3, 4, 5]) == []


def test_group_by_key():
    items = [
        {"name": "Alice", "dept": "eng"},
        {"name": "Bob", "dept": "sales"},
        {"name": "Charlie", "dept": "eng"},
        {"name": "Diana", "dept": "sales"},
        {"name": "Eve", "dept": "eng"},
    ]
    groups = group_by_key(items, lambda x: x["dept"])
    assert list(groups.keys()) == ["eng", "sales"]
    assert [p["name"] for p in groups["eng"]] == ["Alice", "Charlie", "Eve"]
    assert [p["name"] for p in groups["sales"]] == ["Bob", "Diana"]
PY

# Verify baseline
python -m pytest test_processor.py -v

echo "Setup complete. Processor with slow algorithms and 5 passing tests."
