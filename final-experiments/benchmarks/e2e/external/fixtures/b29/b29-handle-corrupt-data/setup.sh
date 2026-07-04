#!/usr/bin/env bash
# Setup for b29-handle-corrupt-data
set -euo pipefail

cat > parser.py << 'PY'
"""CSV parser module."""
import csv


def parse_csv(filepath: str) -> list[dict]:
    """Parse a CSV file into a list of dicts.

    BUG: No error handling for malformed rows.
    Crashes on rows with wrong column count or corrupt data.
    """
    results = []
    with open(filepath, newline="") as f:
        reader = csv.reader(f)
        headers = next(reader)
        for row in reader:
            # BUG: assumes every row has exactly len(headers) columns
            record = {}
            for i, header in enumerate(headers):
                record[header] = row[i]
            results.append(record)
    return results


def get_column(filepath: str, column: str) -> list[str]:
    """Extract a single column from the CSV."""
    data = parse_csv(filepath)
    return [row[column] for row in data]
PY

cat > data.csv << 'CSV'
name,age,city
Alice,30,New York
Bob,25,London
,,,extra,fields,here
Charlie,35,Paris
,
bad row with no commas
Diana,28,Berlin
Eve,,
Frank,40,Tokyo
CSV

cat > test_parser.py << 'PY'
"""Tests for CSV parser with error handling."""
import os
import unittest
from parser import parse_csv


class TestParseCSV(unittest.TestCase):
    def test_parses_good_rows(self):
        """Should correctly parse all valid rows."""
        result = parse_csv("data.csv")
        names = [r["name"] for r in result]
        self.assertIn("Alice", names)
        self.assertIn("Charlie", names)
        self.assertIn("Diana", names)
        self.assertIn("Frank", names)

    def test_skips_bad_rows(self):
        """Should skip rows with wrong column count."""
        result = parse_csv("data.csv")
        # data.csv has 6 rows with data, but some are malformed.
        # Valid rows: Alice, Bob, Charlie, Diana, Frank = 5
        # Bad rows: extra fields row, empty row, no-commas row, Eve (missing city)
        # We accept Eve if the parser handles it, but at minimum 4 good rows
        self.assertGreaterEqual(len(result), 4)
        # Must not have more than 6 (no phantom rows)
        self.assertLessEqual(len(result), 6)

    def test_no_crash(self):
        """Parser must not raise any exceptions."""
        try:
            parse_csv("data.csv")
        except Exception as e:
            self.fail(f"parse_csv raised {type(e).__name__}: {e}")

    def test_correct_fields(self):
        """Parsed rows should have correct field values."""
        result = parse_csv("data.csv")
        alice = [r for r in result if r.get("name") == "Alice"]
        self.assertEqual(len(alice), 1)
        self.assertEqual(alice[0]["age"], "30")
        self.assertEqual(alice[0]["city"], "New York")

    def test_returns_list_of_dicts(self):
        """Each parsed row should be a dict with the header keys."""
        result = parse_csv("data.csv")
        for row in result:
            self.assertIsInstance(row, dict)
            self.assertIn("name", row)


class TestCorruptFile(unittest.TestCase):
    def setUp(self):
        with open("corrupt.csv", "w") as f:
            f.write("a,b,c\n")
            f.write("1,2\n")  # too few columns
            f.write("1,2,3,4\n")  # too many columns
            f.write("x,y,z\n")  # valid

    def tearDown(self):
        os.remove("corrupt.csv")

    def test_handles_column_mismatch(self):
        """Should handle rows with wrong column counts."""
        try:
            result = parse_csv("corrupt.csv")
        except Exception as e:
            self.fail(f"Crashed on corrupt data: {e}")
        # At minimum the valid row should be parsed
        valid = [r for r in result if r.get("a") == "x"]
        self.assertEqual(len(valid), 1)


if __name__ == "__main__":
    unittest.main()
PY

echo "Setup complete. parser.py crashes on malformed CSV rows."
