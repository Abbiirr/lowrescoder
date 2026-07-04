#!/usr/bin/env bash
set -euo pipefail
cd app

ERRORS=0

# Check 1: No f-string SQL injection patterns
if grep -nE "f['\"].*SELECT.*FROM.*WHERE.*\{" app.py 2>/dev/null; then
    echo "FAIL: f-string SQL query still present in app.py"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: No f-string SQL queries"
fi

# Check 2: No % formatting in SQL queries
if grep -nE "execute\(.*%\s" app.py 2>/dev/null; then
    echo "FAIL: %-formatted SQL query found in app.py"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: No %-formatted SQL queries"
fi

# Check 3: No .format() in SQL queries
if grep -nE '(SELECT|INSERT|UPDATE|DELETE).*\.format\(' app.py 2>/dev/null; then
    echo "FAIL: .format() SQL query found in app.py"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: No .format() SQL queries"
fi

# Check 4: Parameterized query is used (? placeholders or named :params)
if grep -qE 'execute\(.*[,]\s*[\(\[]' app.py 2>/dev/null || grep -qE 'execute\(.*\?' app.py 2>/dev/null; then
    echo "PASS: Parameterized query pattern detected"
else
    echo "FAIL: No parameterized query pattern found — expected execute(query, params)"
    ERRORS=$((ERRORS + 1))
fi

# Check 5: Tests still pass
if python -m pytest test_app.py -v 2>&1; then
    echo "PASS: All tests pass"
else
    echo "FAIL: Tests failed"
    ERRORS=$((ERRORS + 1))
fi

if [ "$ERRORS" -gt 0 ]; then
    echo "RESULT: $ERRORS check(s) failed"
    exit 1
fi
echo "RESULT: All checks passed"
exit 0
