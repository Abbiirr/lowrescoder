#!/usr/bin/env bash
# Grading script for b27-one-line-fix
set -euo pipefail

ERRORS=0

# Check 1: Tests pass
if python -m pytest test_counter.py -q 2>&1 | grep -q "passed"; then
    echo "PASS: All tests pass"
else
    echo "FAIL: Tests do not pass"
    ERRORS=$((ERRORS + 1))
fi

# Check 2: Only 1 line changed in counter.py (the < to <=)
# We verify by checking the diff is minimal
CHANGED_LINES=$(diff <(git show HEAD:counter.py 2>/dev/null || cat /dev/null) counter.py 2>/dev/null | grep -c '^[<>]' || true)
if [ "$CHANGED_LINES" -le 2 ]; then
    echo "PASS: Minimal diff (changed lines: $CHANGED_LINES)"
else
    echo "FAIL: Too many lines changed ($CHANGED_LINES), expected 1-2"
    ERRORS=$((ERRORS + 1))
fi

# Check 3: The fix is the <= operator
if grep -q 'while i <= end' counter.py; then
    echo "PASS: Correct fix applied (< changed to <=)"
else
    echo "FAIL: Expected 'while i <= end' in counter.py"
    ERRORS=$((ERRORS + 1))
fi

# Check 4: test_counter.py was not modified
if diff <(git show HEAD:test_counter.py 2>/dev/null || true) test_counter.py > /dev/null 2>&1; then
    echo "PASS: test_counter.py unchanged"
else
    echo "FAIL: test_counter.py was modified (should not be)"
    ERRORS=$((ERRORS + 1))
fi

if [ "$ERRORS" -gt 0 ]; then
    echo "RESULT: $ERRORS check(s) failed"
    exit 1
fi
echo "RESULT: All checks passed"
exit 0
