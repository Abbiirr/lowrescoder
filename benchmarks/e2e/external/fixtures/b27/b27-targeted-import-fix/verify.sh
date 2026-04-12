#!/usr/bin/env bash
# Grading script for b27-targeted-import-fix
set -euo pipefail

ERRORS=0

# Check 1: Program runs without error
if python main.py > /dev/null 2>&1; then
    echo "PASS: main.py runs without errors"
else
    echo "FAIL: main.py crashes on import or execution"
    ERRORS=$((ERRORS + 1))
fi

# Check 2: Tests pass
if python -m pytest test_main.py -q 2>&1 | grep -q "passed"; then
    echo "PASS: All tests pass"
else
    echo "FAIL: Tests do not pass"
    ERRORS=$((ERRORS + 1))
fi

# Check 3: Import points to utils.data_parser
if grep -q 'from utils.data_parser import' main.py; then
    echo "PASS: Import updated to utils.data_parser"
else
    echo "FAIL: Import not updated to utils.data_parser"
    ERRORS=$((ERRORS + 1))
fi

# Check 4: Only the import line changed in main.py
CHANGED_LINES=$(diff <(git show HEAD:main.py 2>/dev/null || cat /dev/null) main.py 2>/dev/null | grep -c '^[<>]' || true)
if [ "$CHANGED_LINES" -le 2 ]; then
    echo "PASS: Minimal change ($CHANGED_LINES diff lines)"
else
    echo "FAIL: Too many lines changed ($CHANGED_LINES), expected only the import line"
    ERRORS=$((ERRORS + 1))
fi

# Check 5: utils/ package not modified
if [ -f utils/parser.py ]; then
    echo "FAIL: utils/parser.py was created (should not exist)"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: No compatibility shim created"
fi

if [ "$ERRORS" -gt 0 ]; then
    echo "RESULT: $ERRORS check(s) failed"
    exit 1
fi
echo "RESULT: All checks passed"
exit 0
