#!/usr/bin/env bash
# Grading script for b17-rename-module
set -euo pipefail

ERRORS=0

# Check 1: helpers.py exists
if [ -f helpers.py ]; then
    echo "PASS: helpers.py exists"
else
    echo "FAIL: helpers.py does not exist"
    ERRORS=$((ERRORS + 1))
fi

# Check 2: utils.py no longer exists
if [ -f utils.py ]; then
    echo "FAIL: utils.py still exists (should be renamed to helpers.py)"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: utils.py removed"
fi

# Check 3: No remaining imports of utils in any Python file
UTILS_IMPORTS=0
for f in app.py models.py services.py api.py test_app.py; do
    if [ -f "$f" ]; then
        if grep -qE '(import utils|from utils import)' "$f"; then
            echo "FAIL: $f still imports from utils"
            UTILS_IMPORTS=$((UTILS_IMPORTS + 1))
        fi
    fi
done

if [ "$UTILS_IMPORTS" -eq 0 ]; then
    echo "PASS: No files import from utils"
else
    ERRORS=$((ERRORS + 1))
fi

# Check 4: Files now import from helpers
HELPERS_IMPORTS=0
for f in app.py models.py services.py api.py test_app.py; do
    if [ -f "$f" ]; then
        if grep -qE '(import helpers|from helpers import)' "$f"; then
            HELPERS_IMPORTS=$((HELPERS_IMPORTS + 1))
        fi
    fi
done

if [ "$HELPERS_IMPORTS" -ge 4 ]; then
    echo "PASS: Files import from helpers ($HELPERS_IMPORTS files)"
else
    echo "FAIL: Expected at least 4 files to import from helpers, found $HELPERS_IMPORTS"
    ERRORS=$((ERRORS + 1))
fi

# Check 5: All tests pass
if python -m pytest test_app.py -v > test_output.log 2>&1; then
    echo "PASS: All tests pass"
else
    echo "FAIL: Tests do not pass"
    tail -20 test_output.log
    ERRORS=$((ERRORS + 1))
fi

# Check 6: helpers.py has the same functions as original utils.py
python3 << 'PYCHECK'
import sys
sys.path.insert(0, ".")
from helpers import slugify, format_date, truncate, validate_email, deep_merge

errors = 0

if slugify("Hello World!") != "hello-world":
    print("FAIL: slugify not working in helpers")
    errors += 1

if not validate_email("test@example.com"):
    print("FAIL: validate_email not working in helpers")
    errors += 1

if errors == 0:
    print("PASS: helpers.py functions work correctly")

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
