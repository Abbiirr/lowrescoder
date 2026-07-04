#!/usr/bin/env bash
set -euo pipefail

mkdir -p project

cat > project/test_data.json << 'PYEOF'
[
  {"name": "Charlie", "score": 85, "id": 1},
  {"name": "Alice", "score": 92, "id": 2},
  {"name": "Bob", "score": 85, "id": 3},
  {"name": "Diana", "score": 92, "id": 4},
  {"name": "Eve", "score": 78, "id": 5},
  {"name": "Frank", "score": 85, "id": 6},
  {"name": "Grace", "score": 92, "id": 7},
  {"name": "Hank", "score": 78, "id": 8},
  {"name": "Iris", "score": 85, "id": 9},
  {"name": "Jack", "score": 100, "id": 10}
]
PYEOF

cat > project/sorter.py << 'PYEOF'
"""Deterministic sorting module."""
import json


def deterministic_sort(items, key):
    """Sort items by the given key in descending order, with stable tie-breaking.

    Items with the same key value must maintain their relative input order
    (stable sort). The output must be identical across multiple runs.

    Args:
        items: List of dicts to sort.
        key: String key name to sort by (descending).

    Returns:
        New sorted list (does not modify input).
    """
    # TODO: Implement deterministic stable sort
    pass


def sort_file(input_path, output_path, key):
    """Read JSON, sort, write JSON.

    Args:
        input_path: Path to input JSON file.
        output_path: Path to output JSON file.
        key: Key to sort by.
    """
    with open(input_path) as f:
        items = json.load(f)
    sorted_items = deterministic_sort(items, key)
    with open(output_path, 'w') as f:
        json.dump(sorted_items, f, indent=2)
PYEOF

cat > project/test_sorter.py << 'PYEOF'
"""Tests for the deterministic sorter."""
import unittest
import json
import os
from sorter import deterministic_sort, sort_file


class TestDeterministicSort(unittest.TestCase):

    def setUp(self):
        data_path = os.path.join(os.path.dirname(__file__), "test_data.json")
        with open(data_path) as f:
            self.data = json.load(f)

    def test_sorted_descending(self):
        result = deterministic_sort(self.data, "score")
        scores = [r["score"] for r in result]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_ties_preserve_input_order(self):
        """Items with score=85 should maintain input order: Charlie, Bob, Frank, Iris."""
        result = deterministic_sort(self.data, "score")
        score_85 = [r["name"] for r in result if r["score"] == 85]
        self.assertEqual(score_85, ["Charlie", "Bob", "Frank", "Iris"])

    def test_ties_92_preserve_order(self):
        """Items with score=92 should maintain input order: Alice, Diana, Grace."""
        result = deterministic_sort(self.data, "score")
        score_92 = [r["name"] for r in result if r["score"] == 92]
        self.assertEqual(score_92, ["Alice", "Diana", "Grace"])

    def test_exact_output(self):
        """Full output must match exactly."""
        result = deterministic_sort(self.data, "score")
        expected_names = ["Jack", "Alice", "Diana", "Grace",
                          "Charlie", "Bob", "Frank", "Iris",
                          "Eve", "Hank"]
        self.assertEqual([r["name"] for r in result], expected_names)

    def test_does_not_modify_input(self):
        original = [d.copy() for d in self.data]
        deterministic_sort(self.data, "score")
        self.assertEqual(self.data, original)

    def test_multiple_runs_identical(self):
        """Running sort 10 times produces identical output every time."""
        results = []
        for _ in range(10):
            result = deterministic_sort(self.data, "score")
            results.append(json.dumps(result))
        self.assertTrue(all(r == results[0] for r in results),
                        "Sort is not deterministic across runs")

    def test_returns_list(self):
        result = deterministic_sort(self.data, "score")
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 10)


if __name__ == "__main__":
    unittest.main()
PYEOF

echo "Setup complete. sorter.py needs deterministic_sort() implemented."
