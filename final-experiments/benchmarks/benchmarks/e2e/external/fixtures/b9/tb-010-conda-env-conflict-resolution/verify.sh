#!/usr/bin/env bash
# Grading script for tb-010-conda-env-conflict-resolution
set -euo pipefail

# Run the resolver
if ! python resolve.py 2>/dev/null; then
    echo "FAIL: resolve.py exited with non-zero status"
    exit 1
fi

# Validate with Python
python3 << 'PYCHECK'
import sys
import re

errors = 0

# Check requirements_fixed.txt exists
try:
    with open("requirements_fixed.txt") as f:
        fixed_lines = [l.strip() for l in f if l.strip() and not l.strip().startswith("#")]
except FileNotFoundError:
    print("FAIL: requirements_fixed.txt not found")
    sys.exit(1)

# Parse package names and constraints
packages = {}
for line in fixed_lines:
    match = re.match(r'^([a-zA-Z0-9_-]+)(.*)', line)
    if match:
        pkg = match.group(1).lower().replace("-", "_")
        constraint = match.group(2).strip()
        if pkg in packages:
            print(f"FAIL: Package '{pkg}' appears more than once")
            errors += 1
        packages[pkg] = constraint

# Check expected packages are present
expected_packages = ["flask", "werkzeug", "sqlalchemy", "requests", "urllib3", "pandas", "numpy", "pytest"]
for pkg in expected_packages:
    if pkg not in packages:
        print(f"FAIL: Missing package '{pkg}' in fixed requirements")
        errors += 1
    else:
        print(f"PASS: Package '{pkg}' present: {pkg}{packages[pkg]}")

# Check conflict resolutions (newer version ranges preferred)
# sqlalchemy should be >=2.0 (not >=1.4,<2.0)
if "sqlalchemy" in packages:
    c = packages["sqlalchemy"]
    if "2.0" in c and ("1.4" not in c or "<2.0" not in c):
        print("PASS: sqlalchemy resolved to newer range (>=2.0)")
    elif ">=2.0" in c:
        print("PASS: sqlalchemy resolved to newer range")
    else:
        print(f"FAIL: sqlalchemy should use newer range (>=2.0,...), got: sqlalchemy{c}")
        errors += 1

# urllib3 should be >=2.0 (not >=1.26,<2.0)
if "urllib3" in packages:
    c = packages["urllib3"]
    if "2.0" in c and "<2.0" not in c:
        print("PASS: urllib3 resolved to newer range (>=2.0)")
    else:
        print(f"FAIL: urllib3 should use newer range (>=2.0), got: urllib3{c}")
        errors += 1

# numpy should be >=1.25 (not >=1.24,<1.25)
if "numpy" in packages:
    c = packages["numpy"]
    if "1.25" in c and "<1.25" not in c:
        print("PASS: numpy resolved to newer range (>=1.25)")
    else:
        print(f"FAIL: numpy should use newer range (>=1.25), got: numpy{c}")
        errors += 1

# pytest should be >=7.0 (not <7.0)
if "pytest" in packages:
    c = packages["pytest"]
    if "7.0" in c and "<7.0" not in c:
        print("PASS: pytest resolved to newer range (>=7.0)")
    else:
        print(f"FAIL: pytest should use newer range (>=7.0), got: pytest{c}")
        errors += 1

# Check no duplicate packages
pkg_counts = {}
for line in fixed_lines:
    match = re.match(r'^([a-zA-Z0-9_-]+)', line)
    if match:
        pkg = match.group(1).lower().replace("-", "_")
        pkg_counts[pkg] = pkg_counts.get(pkg, 0) + 1

for pkg, count in pkg_counts.items():
    if count > 1:
        print(f"FAIL: Package '{pkg}' appears {count} times (must be exactly 1)")
        errors += 1

# Check conflict_report.txt exists and is non-empty
try:
    with open("conflict_report.txt") as f:
        report = f.read().strip()
    if len(report) < 50:
        print("FAIL: conflict_report.txt is too short (need meaningful explanation)")
        errors += 1
    else:
        print(f"PASS: conflict_report.txt exists ({len(report)} chars)")
except FileNotFoundError:
    print("FAIL: conflict_report.txt not found")
    errors += 1

if errors > 0:
    print(f"RESULT: {errors} check(s) failed")
    sys.exit(1)

print("RESULT: All checks passed")
PYCHECK
