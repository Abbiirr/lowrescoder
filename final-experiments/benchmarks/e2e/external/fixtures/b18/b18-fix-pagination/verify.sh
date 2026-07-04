#!/usr/bin/env bash
set -euo pipefail

ERRORS=0

# Check 1: paginator.py exists
if [ ! -f "project/paginator.py" ]; then
    echo "FAIL: project/paginator.py not found"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: project/paginator.py exists"
fi

# Check 2: All tests pass
cd project
TEST_OUTPUT=$(python -m pytest test_paginator.py -v 2>&1) || true
FAILED=$(echo "$TEST_OUTPUT" | grep -c "FAILED" || true)
if [ "$FAILED" -gt 0 ]; then
    echo "FAIL: $FAILED test(s) failed"
    echo "$TEST_OUTPUT" | grep "FAILED"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: All tests pass"
fi
cd ..

# Check 3: Exact division gives correct page count
RESULT=$(cd project && python -c "
from paginator import Paginator
p = Paginator(list(range(20)), page_size=10)
print('OK' if p.total_pages() == 2 else f'FAIL: got {p.total_pages()}')
" 2>&1)
if [ "$RESULT" = "OK" ]; then
    echo "PASS: Exact division page count correct"
else
    echo "FAIL: Exact division page count wrong: $RESULT"
    ERRORS=$((ERRORS + 1))
fi

# Check 4: Last page is not empty
RESULT=$(cd project && python -c "
from paginator import Paginator
p = Paginator(list(range(20)), page_size=10)
last = p.get_page(p.total_pages())
print('OK' if len(last) > 0 else 'FAIL: last page empty')
" 2>&1)
if [ "$RESULT" = "OK" ]; then
    echo "PASS: Last page contains items"
else
    echo "FAIL: Last page problem: $RESULT"
    ERRORS=$((ERRORS + 1))
fi

# Check 5: Remainder case correct
RESULT=$(cd project && python -c "
from paginator import Paginator
p = Paginator(list(range(25)), page_size=10)
print('OK' if p.total_pages() == 3 and len(p.get_page(3)) == 5 else 'FAIL')
" 2>&1)
if [ "$RESULT" = "OK" ]; then
    echo "PASS: Remainder case handled correctly"
else
    echo "FAIL: Remainder case broken: $RESULT"
    ERRORS=$((ERRORS + 1))
fi

# Check 6: All items covered across pages
RESULT=$(cd project && python -c "
from paginator import Paginator
items = list(range(25))
p = Paginator(items, page_size=10)
all_paged = []
for i in range(1, p.total_pages() + 1):
    all_paged.extend(p.get_page(i))
print('OK' if all_paged == items else 'FAIL')
" 2>&1)
if [ "$RESULT" = "OK" ]; then
    echo "PASS: All items covered across pages"
else
    echo "FAIL: Items missing or duplicated: $RESULT"
    ERRORS=$((ERRORS + 1))
fi

if [ "$ERRORS" -gt 0 ]; then
    echo "RESULT: $ERRORS check(s) failed"
    exit 1
fi
echo "RESULT: All checks passed"
exit 0
