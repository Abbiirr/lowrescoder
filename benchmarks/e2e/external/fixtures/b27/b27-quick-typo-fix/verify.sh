#!/usr/bin/env bash
# Grading script for b27-quick-typo-fix
set -euo pipefail

ERRORS=0

# Check 1: Tests pass
if python -m pytest test_api.py -q 2>&1 | grep -q "passed"; then
    echo "PASS: All tests pass"
else
    echo "FAIL: Tests do not pass"
    ERRORS=$((ERRORS + 1))
fi

# Check 2: Function is now correctly named
if grep -q 'def calculate_total' api.py; then
    echo "PASS: Function correctly named calculate_total"
else
    echo "FAIL: Function not renamed to calculate_total"
    ERRORS=$((ERRORS + 1))
fi

# Check 3: Old typo name is gone
if grep -q 'def calcualte_total' api.py; then
    echo "FAIL: Old typo name 'calcualte_total' still present"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: Old typo name removed"
fi

# Check 4: _apply_discount unchanged
if grep -q 'def _apply_discount' api.py; then
    echo "PASS: _apply_discount function preserved"
else
    echo "FAIL: _apply_discount was removed or renamed"
    ERRORS=$((ERRORS + 1))
fi

# Check 5: Minimal diff
CHANGED_LINES=$(diff <(git show HEAD:api.py 2>/dev/null || cat /dev/null) api.py 2>/dev/null | grep -c '^[<>]' || true)
if [ "$CHANGED_LINES" -le 2 ]; then
    echo "PASS: Minimal change ($CHANGED_LINES diff lines)"
else
    echo "FAIL: Too many lines changed ($CHANGED_LINES)"
    ERRORS=$((ERRORS + 1))
fi

# Check 6: test_api.py was not modified
if diff <(git show HEAD:test_api.py 2>/dev/null || true) test_api.py > /dev/null 2>&1; then
    echo "PASS: test_api.py unchanged"
else
    echo "FAIL: test_api.py was modified"
    ERRORS=$((ERRORS + 1))
fi

if [ "$ERRORS" -gt 0 ]; then
    echo "RESULT: $ERRORS check(s) failed"
    exit 1
fi
echo "RESULT: All checks passed"
exit 0
