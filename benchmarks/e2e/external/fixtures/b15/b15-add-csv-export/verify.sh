#!/usr/bin/env bash
# Grading script for b15-add-csv-export
set -euo pipefail

ERRORS=0

# Check 1: export_csv function exists somewhere
EXPORT_FOUND=0
for f in report.py export.py csv_export.py; do
    if [ -f "$f" ] && grep -qE 'def export_csv' "$f"; then
        EXPORT_FOUND=1
        echo "PASS: export_csv function found in $f"
        break
    fi
done

if [ "$EXPORT_FOUND" -eq 0 ]; then
    echo "FAIL: export_csv function not found"
    ERRORS=$((ERRORS + 1))
fi

# Check 2: Existing tests still pass
if python -m pytest test_report.py -v > test_output.log 2>&1; then
    echo "PASS: Existing tests pass"
else
    echo "FAIL: Existing tests broken"
    tail -20 test_output.log
    ERRORS=$((ERRORS + 1))
fi

# Check 3: CSV output is valid and complete
python3 << 'PYCHECK'
import sys
import csv
import os

sys.path.insert(0, ".")

# Try importing export_csv from various possible locations
export_csv = None
for module_name in ["report", "export", "csv_export"]:
    try:
        mod = __import__(module_name)
        if hasattr(mod, "export_csv"):
            export_csv = mod.export_csv
            break
    except ImportError:
        continue

if export_csv is None:
    print("FAIL: Could not import export_csv")
    sys.exit(1)

from report import get_monthly_report

data = get_monthly_report(2025, 1)
output_path = "test_export.csv"

# Call export_csv — try common signatures
try:
    export_csv(data, output_path)
except TypeError:
    try:
        export_csv(data, filepath=output_path)
    except TypeError:
        try:
            export_csv(data, filename=output_path)
        except TypeError:
            print("FAIL: Could not call export_csv with (data, path) signature")
            sys.exit(1)

errors = 0

if not os.path.exists(output_path):
    print("FAIL: CSV file was not created")
    sys.exit(1)
else:
    print("PASS: CSV file created")

with open(output_path, "r") as f:
    reader = csv.DictReader(f)
    rows = list(reader)

# Check headers
expected_headers = {"date", "product", "quantity", "unit_price", "total"}
actual_headers = set(reader.fieldnames) if reader.fieldnames else set()
if not expected_headers.issubset(actual_headers):
    print(f"FAIL: CSV headers wrong. Expected {expected_headers}, got {actual_headers}")
    errors += 1
else:
    print("PASS: CSV headers correct")

# Check row count
if len(rows) != 10:
    print(f"FAIL: Expected 10 data rows, got {len(rows)}")
    errors += 1
else:
    print("PASS: CSV has correct number of rows")

# Check sample data
if rows:
    first = rows[0]
    if first.get("product") == "Widget A":
        print("PASS: Sample data verified")
    else:
        print(f"FAIL: First row product should be 'Widget A', got '{first.get('product')}'")
        errors += 1

# Cleanup
os.remove(output_path)

sys.exit(errors)
PYCHECK

PYCHECK_EXIT=$?
if [ "$PYCHECK_EXIT" -ne 0 ]; then
    ERRORS=$((ERRORS + PYCHECK_EXIT))
fi

# Result
if [ "$ERRORS" -gt 0 ]; then
    echo "RESULT: $ERRORS check(s) failed"
    exit 1
fi

echo "RESULT: All checks passed"
exit 0
