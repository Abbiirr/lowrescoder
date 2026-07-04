#!/usr/bin/env bash
set -euo pipefail

mkdir -p project

cat > project/input.csv << 'EOF'
id,name,email,age,department,salary,active
1,Alice Johnson,alice@example.com,32,Engineering,95000,true
2,Bob Smith,bob@example.com,28,Marketing,62000,true
3,Charlie Brown,charlie@example.com,45,Engineering,120000,true
4,Diana Prince,diana@example.com,38,HR,78000,false
5,Eve Wilson,eve@example.com,25,Engineering,72000,true
6,Frank Castle,frank@example.com,52,Marketing,85000,true
7,Grace Lee,grace@example.com,29,Engineering,88000,true
8,Hank Pym,hank@example.com,41,Research,110000,false
9,Iris West,iris@example.com,33,Marketing,67000,true
10,Jack Ryan,jack@example.com,36,Engineering,102000,true
11,Kate Bishop,kate@example.com,24,HR,55000,true
12,Leo Messi,leo@example.com,37,Marketing,71000,false
EOF

cat > project/transform_spec.md << 'EOF'
# Data Transformation Specification

## Input
CSV file with columns: id, name, email, age, department, salary, active

## Transformations
1. **Filter**: Only include rows where `active` is `true`
2. **Filter**: Only include rows where `salary` >= 70000
3. **Transform**: Add a `salary_band` field:
   - salary < 80000: "junior"
   - 80000 <= salary < 100000: "mid"
   - salary >= 100000: "senior"
4. **Transform**: Extract first name from `name` field into `first_name`
5. **Transform**: Convert `age` and `salary` to integers, `id` to integer
6. **Select**: Output only: `id`, `first_name`, `email`, `department`, `salary`, `salary_band`

## Output
JSON array of objects, sorted by salary descending.
EOF

cat > project/expected_output.json << 'PYEOF'
[
  {"id": 10, "first_name": "Jack", "email": "jack@example.com", "department": "Engineering", "salary": 102000, "salary_band": "senior"},
  {"id": 1, "first_name": "Alice", "email": "alice@example.com", "department": "Engineering", "salary": 95000, "salary_band": "mid"},
  {"id": 7, "first_name": "Grace", "email": "grace@example.com", "department": "Engineering", "salary": 88000, "salary_band": "mid"},
  {"id": 6, "first_name": "Frank", "email": "frank@example.com", "department": "Marketing", "salary": 85000, "salary_band": "mid"},
  {"id": 5, "first_name": "Eve", "email": "eve@example.com", "department": "Engineering", "salary": 72000, "salary_band": "junior"}
]
PYEOF

cat > project/pipeline.py << 'PYEOF'
"""Data transformation pipeline — CSV to filtered JSON.

Usage: python pipeline.py input.csv output.json
"""
import csv
import json
import sys


def run_pipeline(input_path, output_path):
    """Read CSV, apply transformations, write JSON.

    Args:
        input_path: Path to input CSV file.
        output_path: Path to output JSON file.
    """
    # TODO: Implement the transformation pipeline per transform_spec.md
    pass


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python pipeline.py input.csv output.json")
        sys.exit(1)
    run_pipeline(sys.argv[1], sys.argv[2])
PYEOF

cat > project/test_pipeline.py << 'PYEOF'
"""Tests for the data transformation pipeline."""
import unittest
import json
import os
import tempfile
from pipeline import run_pipeline


class TestPipeline(unittest.TestCase):

    def setUp(self):
        self.input_path = os.path.join(os.path.dirname(__file__), "input.csv")
        self.expected_path = os.path.join(os.path.dirname(__file__), "expected_output.json")
        self.output_fd, self.output_path = tempfile.mkstemp(suffix=".json")
        os.close(self.output_fd)

    def tearDown(self):
        if os.path.exists(self.output_path):
            os.unlink(self.output_path)

    def _load_expected(self):
        with open(self.expected_path) as f:
            return json.load(f)

    def _load_output(self):
        with open(self.output_path) as f:
            return json.load(f)

    def test_pipeline_produces_output(self):
        run_pipeline(self.input_path, self.output_path)
        self.assertTrue(os.path.exists(self.output_path))
        output = self._load_output()
        self.assertIsInstance(output, list)

    def test_correct_record_count(self):
        """Only active employees with salary >= 70000 should be included."""
        run_pipeline(self.input_path, self.output_path)
        output = self._load_output()
        self.assertEqual(len(output), 5)

    def test_inactive_filtered(self):
        """Inactive employees should not appear."""
        run_pipeline(self.input_path, self.output_path)
        output = self._load_output()
        names = [r["first_name"] for r in output]
        self.assertNotIn("Diana", names)  # active=false
        self.assertNotIn("Hank", names)   # active=false
        self.assertNotIn("Leo", names)    # active=false

    def test_low_salary_filtered(self):
        """Employees with salary < 70000 should not appear."""
        run_pipeline(self.input_path, self.output_path)
        output = self._load_output()
        names = [r["first_name"] for r in output]
        self.assertNotIn("Bob", names)    # salary=62000
        self.assertNotIn("Iris", names)   # salary=67000
        self.assertNotIn("Kate", names)   # salary=55000

    def test_salary_bands(self):
        run_pipeline(self.input_path, self.output_path)
        output = self._load_output()
        bands = {r["first_name"]: r["salary_band"] for r in output}
        self.assertEqual(bands.get("Jack"), "senior")   # 102000
        self.assertEqual(bands.get("Alice"), "mid")     # 95000
        self.assertEqual(bands.get("Eve"), "junior")    # 72000

    def test_sorted_by_salary_desc(self):
        run_pipeline(self.input_path, self.output_path)
        output = self._load_output()
        salaries = [r["salary"] for r in output]
        self.assertEqual(salaries, sorted(salaries, reverse=True))

    def test_correct_fields(self):
        """Output should have exactly the specified fields."""
        run_pipeline(self.input_path, self.output_path)
        output = self._load_output()
        expected_keys = {"id", "first_name", "email", "department", "salary", "salary_band"}
        for record in output:
            self.assertEqual(set(record.keys()), expected_keys)

    def test_matches_expected_output(self):
        run_pipeline(self.input_path, self.output_path)
        output = self._load_output()
        expected = self._load_expected()
        self.assertEqual(output, expected)


if __name__ == "__main__":
    unittest.main()
PYEOF

echo "Setup complete. pipeline.py needs transformation logic implemented."
