#!/usr/bin/env bash
set -euo pipefail

ERRORS=0

# Check 1: validator.py exists
if [ ! -f "project/validator.py" ]; then
    echo "FAIL: project/validator.py not found"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: project/validator.py exists"
fi

# Check 2: validate_email is implemented (not just pass)
if [ -f "project/validator.py" ]; then
    IMPL_CHECK=$(cd project && python -c "
from validator import validate_email
r = validate_email('user@example.com')
print('OK' if r is not None and isinstance(r, dict) else 'FAIL')
" 2>&1)
    if [ "$IMPL_CHECK" = "OK" ]; then
        echo "PASS: validate_email is implemented"
    else
        echo "FAIL: validate_email not implemented: $IMPL_CHECK"
        ERRORS=$((ERRORS + 1))
    fi
fi

# Check 3: All tests pass
cd project
TEST_OUTPUT=$(python -m pytest test_validator.py -v 2>&1) || true
FAILED=$(echo "$TEST_OUTPUT" | grep -c "FAILED" || true)
if [ "$FAILED" -gt 0 ]; then
    echo "FAIL: $FAILED test(s) failed"
    echo "$TEST_OUTPUT" | grep "FAILED"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: All tests pass"
fi
cd ..

# Check 4: Valid email accepted
RESULT=$(cd project && python -c "
from validator import validate_email
r = validate_email('user@example.com')
print('OK' if r['valid'] and r['reason'] == 'ok' else f'FAIL: {r}')
" 2>&1)
if [ "$RESULT" = "OK" ]; then
    echo "PASS: Valid email accepted"
else
    echo "FAIL: Valid email not accepted: $RESULT"
    ERRORS=$((ERRORS + 1))
fi

# Check 5: Invalid email rejected
RESULT=$(cd project && python -c "
from validator import validate_email
r = validate_email('bad')
print('OK' if not r['valid'] else f'FAIL: {r}')
" 2>&1)
if [ "$RESULT" = "OK" ]; then
    echo "PASS: Invalid email rejected"
else
    echo "FAIL: Invalid email not rejected: $RESULT"
    ERRORS=$((ERRORS + 1))
fi

# Check 6: Disposable domain rejected
RESULT=$(cd project && python -c "
from validator import validate_email
r = validate_email('test@mailinator.com')
print('OK' if not r['valid'] and 'disposable' in r['reason'].lower() else f'FAIL: {r}')
" 2>&1)
if [ "$RESULT" = "OK" ]; then
    echo "PASS: Disposable domain rejected"
else
    echo "FAIL: Disposable domain not rejected: $RESULT"
    ERRORS=$((ERRORS + 1))
fi

if [ "$ERRORS" -gt 0 ]; then
    echo "RESULT: $ERRORS check(s) failed"
    exit 1
fi
echo "RESULT: All checks passed"
exit 0
