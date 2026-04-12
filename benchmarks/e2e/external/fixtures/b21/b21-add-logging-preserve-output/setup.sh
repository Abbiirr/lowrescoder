#!/usr/bin/env bash
set -euo pipefail

pip install pytest --quiet

cat > input.csv << 'CSV'
name,score,grade
Alice,95,A
Bob,82,B
Charlie,67,D
Diana,91,A
Eve,55,F
CSV

cat > pipeline.py << 'PY'
"""Data processing pipeline. Reads CSV, transforms, writes to stdout."""
import csv
import sys


def load_records(filepath):
    """Load records from a CSV file."""
    records = []
    with open(filepath, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["score"] = int(row["score"])
            records.append(row)
    return records


def transform(records):
    """Filter passing students and add pass/fail status."""
    results = []
    for r in records:
        entry = {
            "name": r["name"],
            "score": r["score"],
            "status": "PASS" if r["score"] >= 60 else "FAIL",
        }
        results.append(entry)
    return results


def format_output(results):
    """Format results as tab-separated output."""
    lines = ["NAME\tSCORE\tSTATUS"]
    for r in results:
        lines.append(f"{r['name']}\t{r['score']}\t{r['status']}")
    lines.append(f"---\nTotal: {len(results)} students")
    passing = sum(1 for r in results if r["status"] == "PASS")
    lines.append(f"Passing: {passing}/{len(results)}")
    return "\n".join(lines)


def main(filepath):
    records = load_records(filepath)
    results = transform(records)
    output = format_output(results)
    print(output)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: pipeline.py <input.csv>", file=sys.stderr)
        sys.exit(1)
    main(sys.argv[1])
PY

# Capture expected output for tests
EXPECTED_OUTPUT=$(python pipeline.py input.csv)

cat > test_pipeline.py << PY
import subprocess
import pytest
from pipeline import load_records, transform, format_output


EXPECTED_OUTPUT = """$EXPECTED_OUTPUT"""


def test_stdout_output():
    result = subprocess.run(
        ["python", "pipeline.py", "input.csv"],
        capture_output=True, text=True
    )
    assert result.stdout.strip() == EXPECTED_OUTPUT.strip()
    assert result.returncode == 0


def test_load_records():
    records = load_records("input.csv")
    assert len(records) == 5
    assert records[0]["name"] == "Alice"
    assert records[0]["score"] == 95


def test_transform():
    records = [
        {"name": "A", "score": 90, "grade": "A"},
        {"name": "B", "score": 50, "grade": "F"},
    ]
    results = transform(records)
    assert results[0]["status"] == "PASS"
    assert results[1]["status"] == "FAIL"


def test_format_output():
    results = [{"name": "Test", "score": 80, "status": "PASS"}]
    output = format_output(results)
    assert "NAME\tSCORE\tSTATUS" in output
    assert "Test\t80\tPASS" in output
    assert "Total: 1" in output
PY

# Verify baseline
python -m pytest test_pipeline.py -v

echo "Setup complete. Data pipeline with deterministic output and 4 passing tests."
