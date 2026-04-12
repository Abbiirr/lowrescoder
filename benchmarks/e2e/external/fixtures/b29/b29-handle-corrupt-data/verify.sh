#!/usr/bin/env bash
# Grading script for b29-handle-corrupt-data
set -euo pipefail

ERRORS=0

# Check 1: All tests pass
if python -m pytest test_parser.py -q 2>&1 | grep -q "passed"; then
    echo "PASS: All tests pass"
else
    echo "FAIL: Some tests fail"
    python -m pytest test_parser.py -q 2>&1 | tail -5
    ERRORS=$((ERRORS + 1))
fi

# Check 2: Parser doesn't crash on the included data.csv
if python -c "from parser import parse_csv; parse_csv('data.csv')" 2>/dev/null; then
    echo "PASS: Parser handles data.csv without crashing"
else
    echo "FAIL: Parser crashes on data.csv"
    ERRORS=$((ERRORS + 1))
fi

# Check 3: Parser returns correct good rows
GOOD_COUNT=$(python -c "
from parser import parse_csv
rows = parse_csv('data.csv')
print(len([r for r in rows if r.get('name') in ('Alice','Bob','Charlie','Diana','Frank')]))
" 2>/dev/null || echo "0")
if [ "$GOOD_COUNT" -ge 4 ]; then
    echo "PASS: At least 4 valid rows parsed ($GOOD_COUNT)"
else
    echo "FAIL: Too few valid rows parsed ($GOOD_COUNT)"
    ERRORS=$((ERRORS + 1))
fi

# Check 4: Error handling exists in code
if grep -qE '(try|except|IndexError|ValueError|continue)' parser.py; then
    echo "PASS: Error handling code found in parser.py"
else
    echo "FAIL: No error handling found in parser.py"
    ERRORS=$((ERRORS + 1))
fi

# Check 5: data.csv was not modified
if diff <(git show HEAD:data.csv 2>/dev/null || true) data.csv > /dev/null 2>&1; then
    echo "PASS: data.csv unchanged"
else
    echo "FAIL: data.csv was modified"
    ERRORS=$((ERRORS + 1))
fi

if [ "$ERRORS" -gt 0 ]; then
    echo "RESULT: $ERRORS check(s) failed"
    exit 1
fi
echo "RESULT: All checks passed"
exit 0
