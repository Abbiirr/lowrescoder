#!/usr/bin/env bash
# Grading script for b29-handle-network-timeout
set -euo pipefail

ERRORS=0

# Check 1: All tests pass
if python -m pytest test_client.py -q 2>&1 | grep -q "passed"; then
    echo "PASS: All tests pass"
else
    echo "FAIL: Some tests fail"
    python -m pytest test_client.py -q 2>&1 | tail -5
    ERRORS=$((ERRORS + 1))
fi

# Check 2: timeout parameter exists in code
if grep -q 'timeout' client.py; then
    echo "PASS: timeout parameter found in client.py"
else
    echo "FAIL: No timeout parameter in client.py"
    ERRORS=$((ERRORS + 1))
fi

# Check 3: Retry logic exists (loop or recursion or retry library)
if grep -qE '(for|while|retry|range|attempt)' client.py; then
    echo "PASS: Retry logic found in client.py"
else
    echo "FAIL: No retry logic found in client.py"
    ERRORS=$((ERRORS + 1))
fi

# Check 4: Exception handling for timeout/connection errors
if grep -qE '(Timeout|ConnectionError|except)' client.py; then
    echo "PASS: Exception handling for network errors found"
else
    echo "FAIL: No exception handling for network errors"
    ERRORS=$((ERRORS + 1))
fi

# Check 5: test_client.py was not modified
if diff <(git show HEAD:test_client.py 2>/dev/null || true) test_client.py > /dev/null 2>&1; then
    echo "PASS: test_client.py unchanged"
else
    echo "FAIL: test_client.py was modified"
    ERRORS=$((ERRORS + 1))
fi

if [ "$ERRORS" -gt 0 ]; then
    echo "RESULT: $ERRORS check(s) failed"
    exit 1
fi
echo "RESULT: All checks passed"
exit 0
