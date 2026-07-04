#!/usr/bin/env bash
set -euo pipefail

ERRORS=0

# Check 1: All 5 original tests pass
TEST_RESULT=$(python -m pytest test_processor.py -v 2>&1)
PASSED=$(echo "$TEST_RESULT" | grep -c " PASSED" || true)

if [ "$PASSED" -ge 5 ]; then
    echo "PASS: All 5 original tests pass"
else
    echo "FAIL: Tests broken ($PASSED/5 passed)"
    echo "$TEST_RESULT"
    ERRORS=$((ERRORS + 1))
fi

# Check 2: Output identical for custom_sort
SORT_CHECK=$(python -c "
from processor import custom_sort
assert custom_sort([5,3,8,1,9,2]) == [1,2,3,5,8,9]
assert custom_sort([]) == []
assert custom_sort([1]) == [1]
assert custom_sort(['z','a','m']) == ['a','m','z']
print('ok')
" 2>&1)

if [ "$SORT_CHECK" = "ok" ]; then
    echo "PASS: custom_sort output identical"
else
    echo "FAIL: custom_sort output changed: $SORT_CHECK"
    ERRORS=$((ERRORS + 1))
fi

# Check 3: Output identical for find_duplicates
DUP_CHECK=$(python -c "
from processor import find_duplicates
assert find_duplicates([1,2,3,2,4,5,1,6,3]) == [1,2,3]
assert find_duplicates([1,2,3]) == []
assert find_duplicates([1,1,1]) == [1]
print('ok')
" 2>&1)

if [ "$DUP_CHECK" = "ok" ]; then
    echo "PASS: find_duplicates output identical"
else
    echo "FAIL: find_duplicates output changed: $DUP_CHECK"
    ERRORS=$((ERRORS + 1))
fi

# Check 4: Output identical for group_by_key
GROUP_CHECK=$(python -c "
from processor import group_by_key
items = [
    {'name': 'Alice', 'dept': 'eng'},
    {'name': 'Bob', 'dept': 'sales'},
    {'name': 'Charlie', 'dept': 'eng'},
]
groups = group_by_key(items, lambda x: x['dept'])
assert list(groups.keys()) == ['eng', 'sales']
assert len(groups['eng']) == 2
assert groups['eng'][0]['name'] == 'Alice'
print('ok')
" 2>&1)

if [ "$GROUP_CHECK" = "ok" ]; then
    echo "PASS: group_by_key output identical"
else
    echo "FAIL: group_by_key output changed: $GROUP_CHECK"
    ERRORS=$((ERRORS + 1))
fi

# Check 5: Function signatures unchanged
SIG_CHECK=$(python -c "
import inspect
from processor import custom_sort, find_duplicates, group_by_key
assert list(inspect.signature(custom_sort).parameters.keys()) == ['items']
assert list(inspect.signature(find_duplicates).parameters.keys()) == ['items']
assert list(inspect.signature(group_by_key).parameters.keys()) == ['items', 'key_fn']
print('ok')
" 2>&1)

if [ "$SIG_CHECK" = "ok" ]; then
    echo "PASS: Function signatures unchanged"
else
    echo "FAIL: Signatures changed: $SIG_CHECK"
    ERRORS=$((ERRORS + 1))
fi

# Check 6 (bonus): Performance improved — bubble sort is gone
if grep -q "bubble\|for j in range.*n - i" processor.py; then
    echo "INFO: Bubble sort still present (optimization not applied, but correctness OK)"
else
    echo "PASS: Bubble sort removed (optimization applied)"
fi

if [ "$ERRORS" -gt 0 ]; then
    echo "RESULT: $ERRORS check(s) failed"
    exit 1
fi
echo "RESULT: All checks passed"
exit 0
