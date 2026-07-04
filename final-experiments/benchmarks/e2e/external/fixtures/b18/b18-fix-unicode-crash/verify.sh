#!/usr/bin/env bash
set -euo pipefail

ERRORS=0

# Check 1: search.py exists
if [ ! -f "project/search.py" ]; then
    echo "FAIL: project/search.py not found"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: project/search.py exists"
fi

# Check 2: No ascii encoding in search.py (the bug)
if grep -q "encode('ascii')" project/search.py 2>/dev/null; then
    echo "FAIL: search.py still uses ascii encoding (the bug)"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: ascii encoding removed from search.py"
fi

# Check 3: All tests pass
cd project
TEST_OUTPUT=$(python -m pytest test_search.py -v 2>&1) || true
FAILED=$(echo "$TEST_OUTPUT" | grep -c "FAILED" || true)
if [ "$FAILED" -gt 0 ]; then
    echo "FAIL: $FAILED test(s) failed"
    echo "$TEST_OUTPUT" | grep "FAILED"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: All tests pass"
fi
cd ..

# Check 4: Unicode search works at runtime
RESULT=$(cd project && python -c "
from search import search
r = search('café', ['Café Latte', 'Green Tea'])
print('OK' if 'Café Latte' in r else 'FAIL')
" 2>&1)
if [ "$RESULT" = "OK" ]; then
    echo "PASS: Unicode search works at runtime"
else
    echo "FAIL: Unicode search broken at runtime: $RESULT"
    ERRORS=$((ERRORS + 1))
fi

# Check 5: CJK search works
RESULT=$(cd project && python -c "
from search import search
r = search('東京', ['東京タワー', '富士山'])
print('OK' if '東京タワー' in r else 'FAIL')
" 2>&1)
if [ "$RESULT" = "OK" ]; then
    echo "PASS: CJK search works"
else
    echo "FAIL: CJK search broken: $RESULT"
    ERRORS=$((ERRORS + 1))
fi

# Check 6: Function signatures unchanged
SIG_CHECK=$(cd project && python -c "
import inspect
from search import search, search_exact
s1 = inspect.signature(search)
s2 = inspect.signature(search_exact)
params1 = list(s1.parameters.keys())
params2 = list(s2.parameters.keys())
if params1 == ['query', 'items'] and params2 == ['query', 'items']:
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
