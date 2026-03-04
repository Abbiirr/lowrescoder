#!/usr/bin/env bash
# Grading script for tb-004-csv-to-parquet
set -euo pipefail

ERRORS=0

# Step 1: Run the conversion script
if ! python convert.py 2>/dev/null; then
    echo "FAIL: convert.py exited with non-zero status"
    exit 1
fi

# Step 2: Check output file exists
if [ ! -f output.parquet ]; then
    echo "FAIL: output.parquet was not created"
    exit 1
fi

# Step 3: Validate the parquet file content
python3 << 'PYCHECK'
import sys

try:
    import pandas as pd
except ImportError:
    print("FAIL: pandas not available")
    sys.exit(1)

try:
    df = pd.read_parquet("output.parquet")
except Exception as e:
    print(f"FAIL: Could not read output.parquet: {e}")
    sys.exit(1)

errors = 0

# Check row count
if len(df) != 25:
    print(f"FAIL: Expected 25 rows, got {len(df)}")
    errors += 1
else:
    print("PASS: Row count is 25")

# Check columns
expected_cols = {"id", "name", "age", "city", "salary"}
actual_cols = set(df.columns)
if expected_cols != actual_cols:
    print(f"FAIL: Expected columns {expected_cols}, got {actual_cols}")
    errors += 1
else:
    print("PASS: All columns present")

# Check a sample value
alice_rows = df[df["name"] == "Alice"]
if len(alice_rows) == 0:
    print("FAIL: Could not find row with name='Alice'")
    errors += 1
else:
    alice = alice_rows.iloc[0]
    if alice["city"] != "New York":
        print(f"FAIL: Alice's city should be 'New York', got '{alice['city']}'")
        errors += 1
    else:
        print("PASS: Sample data verified (Alice in New York)")

if errors > 0:
    print(f"RESULT: {errors} check(s) failed")
    sys.exit(1)

print("RESULT: All checks passed")
PYCHECK
