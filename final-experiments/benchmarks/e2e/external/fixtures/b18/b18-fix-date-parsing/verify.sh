#!/usr/bin/env bash
set -euo pipefail

ERRORS=0

# Check 1: dateparser.py exists
if [ ! -f "project/dateparser.py" ]; then
    echo "FAIL: project/dateparser.py not found"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: project/dateparser.py exists"
fi

# Check 2: All tests pass
cd project
TEST_OUTPUT=$(python -m pytest test_dateparser.py -v 2>&1) || true
FAILED=$(echo "$TEST_OUTPUT" | grep -c "FAILED" || true)
if [ "$FAILED" -gt 0 ]; then
    echo "FAIL: $FAILED test(s) failed"
    echo "$TEST_OUTPUT" | grep "FAILED"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: All tests pass"
fi
cd ..

# Check 3: Positive offset parsing works
RESULT=$(cd project && python -c "
from dateparser import parse_date
dt = parse_date('2024-01-15T10:30:00+05:30')
print('OK' if dt.utcoffset() is not None else 'FAIL')
" 2>&1)
if [ "$RESULT" = "OK" ]; then
    echo "PASS: Positive offset parsing works"
else
    echo "FAIL: Positive offset parsing broken: $RESULT"
    ERRORS=$((ERRORS + 1))
fi

# Check 4: Negative offset parsing works
RESULT=$(cd project && python -c "
from dateparser import parse_date
dt = parse_date('2024-01-15T10:30:00-08:00')
print('OK' if dt.utcoffset() is not None else 'FAIL')
" 2>&1)
if [ "$RESULT" = "OK" ]; then
    echo "PASS: Negative offset parsing works"
else
    echo "FAIL: Negative offset parsing broken: $RESULT"
    ERRORS=$((ERRORS + 1))
fi

# Check 5: Naive dates still work
RESULT=$(cd project && python -c "
from dateparser import parse_date
dt = parse_date('2024-01-15')
print('OK' if dt.year == 2024 else 'FAIL')
" 2>&1)
if [ "$RESULT" = "OK" ]; then
    echo "PASS: Naive dates still work"
else
    echo "FAIL: Naive dates broken: $RESULT"
    ERRORS=$((ERRORS + 1))
fi

# Check 6: Function signatures unchanged
SIG_CHECK=$(cd project && python -c "
import inspect
from dateparser import parse_date, format_date
s1 = list(inspect.signature(parse_date).parameters.keys())
s2 = list(inspect.signature(format_date).parameters.keys())
if s1 == ['date_string'] and s2 == ['dt', 'include_tz']:
    print('OK')
else:
    print('FAIL')
" 2>&1)
if [ "$SIG_CHECK" = "OK" ]; then
    echo "PASS: Function signatures unchanged"
else
    echo "FAIL: Function signatures were modified"
    ERRORS=$((ERRORS + 1))
fi

if [ "$ERRORS" -gt 0 ]; then
    echo "RESULT: $ERRORS check(s) failed"
    exit 1
fi
echo "RESULT: All checks passed"
exit 0
