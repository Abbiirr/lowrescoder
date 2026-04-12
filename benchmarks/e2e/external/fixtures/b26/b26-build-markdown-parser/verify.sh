#!/usr/bin/env bash
set -euo pipefail

ERRORS=0

# Check 1: markdown_parser.py exists
if [ ! -f "project/markdown_parser.py" ]; then
    echo "FAIL: project/markdown_parser.py not found"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: project/markdown_parser.py exists"
fi

# Check 2: convert() is implemented
if [ -f "project/markdown_parser.py" ]; then
    IMPL_CHECK=$(cd project && python -c "
from markdown_parser import convert
r = convert('# Hello')
print('OK' if r is not None and len(r) > 0 else 'FAIL')
" 2>&1)
    if [ "$IMPL_CHECK" = "OK" ]; then
        echo "PASS: convert() is implemented"
    else
        echo "FAIL: convert() not implemented: $IMPL_CHECK"
        ERRORS=$((ERRORS + 1))
    fi
fi

# Check 3: All tests pass
cd project
TEST_OUTPUT=$(python -m pytest test_parser.py -v 2>&1) || true
FAILED=$(echo "$TEST_OUTPUT" | grep -c "FAILED" || true)
if [ "$FAILED" -gt 0 ]; then
    echo "FAIL: $FAILED test(s) failed"
    echo "$TEST_OUTPUT" | grep "FAILED"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: All tests pass"
fi
cd ..

# Check 4: Headings work
RESULT=$(cd project && python -c "
from markdown_parser import convert
r = convert('## Hello')
print('OK' if '<h2>Hello</h2>' in r.strip() else f'FAIL: {r}')
" 2>&1)
if [ "$RESULT" = "OK" ]; then
    echo "PASS: Headings convert correctly"
else
    echo "FAIL: Headings broken: $RESULT"
    ERRORS=$((ERRORS + 1))
fi

# Check 5: Bold works
RESULT=$(cd project && python -c "
from markdown_parser import convert
r = convert('**bold**')
print('OK' if '<strong>bold</strong>' in r else f'FAIL: {r}')
" 2>&1)
if [ "$RESULT" = "OK" ]; then
    echo "PASS: Bold converts correctly"
else
    echo "FAIL: Bold broken: $RESULT"
    ERRORS=$((ERRORS + 1))
fi

# Check 6: Links work
RESULT=$(cd project && python -c "
from markdown_parser import convert
r = convert('[Click](https://example.com)')
print('OK' if '<a href=\"https://example.com\">Click</a>' in r else f'FAIL: {r}')
" 2>&1)
if [ "$RESULT" = "OK" ]; then
    echo "PASS: Links convert correctly"
else
    echo "FAIL: Links broken: $RESULT"
    ERRORS=$((ERRORS + 1))
fi

if [ "$ERRORS" -gt 0 ]; then
    echo "RESULT: $ERRORS check(s) failed"
    exit 1
fi
echo "RESULT: All checks passed"
exit 0
