#!/usr/bin/env bash
set -euo pipefail

ERRORS=0

# Check 1: sorter.py exists
if [ ! -f "project/sorter.py" ]; then
    echo "FAIL: project/sorter.py not found"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: project/sorter.py exists"
fi

# Check 2: All tests pass
cd project
TEST_OUTPUT=$(python -m pytest test_sorter.py -v 2>&1) || true
FAILED=$(echo "$TEST_OUTPUT" | grep -c "FAILED" || true)
if [ "$FAILED" -gt 0 ]; then
    echo "FAIL: $FAILED test(s) failed"
    echo "$TEST_OUTPUT" | grep "FAILED"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: All tests pass"
fi
cd ..

# Check 3: Exact output order
RESULT=$(cd project && python -c "
import json
from sorter import deterministic_sort
with open('test_data.json') as f: data = json.load(f)
result = deterministic_sort(data, 'score')
names = [r['name'] for r in result]
expected = ['Jack', 'Alice', 'Diana', 'Grace', 'Charlie', 'Bob', 'Frank', 'Iris', 'Eve', 'Hank']
print('OK' if names == expected else f'FAIL: {names}')
" 2>&1)
if [ "$RESULT" = "OK" ]; then
    echo "PASS: Exact output order correct"
else
    echo "FAIL: Output order wrong: $RESULT"
    ERRORS=$((ERRORS + 1))
fi

# Check 4: Deterministic across 5 runs
RESULT=$(cd project && python -c "
import json
from sorter import deterministic_sort
with open('test_data.json') as f: data = json.load(f)
outputs = set()
for _ in range(5):
    result = deterministic_sort(data, 'score')
    outputs.add(json.dumps(result))
print('OK' if len(outputs) == 1 else 'FAIL: non-deterministic')
" 2>&1)
if [ "$RESULT" = "OK" ]; then
    echo "PASS: Deterministic across 5 runs"
else
    echo "FAIL: Non-deterministic: $RESULT"
    ERRORS=$((ERRORS + 1))
fi

# Check 5: Sorted descending by score
RESULT=$(cd project && python -c "
import json
from sorter import deterministic_sort
with open('test_data.json') as f: data = json.load(f)
result = deterministic_sort(data, 'score')
scores = [r['score'] for r in result]
print('OK' if scores == sorted(scores, reverse=True) else 'FAIL')
" 2>&1)
if [ "$RESULT" = "OK" ]; then
    echo "PASS: Sorted descending by score"
else
    echo "FAIL: Not sorted correctly: $RESULT"
    ERRORS=$((ERRORS + 1))
fi

if [ "$ERRORS" -gt 0 ]; then
    echo "RESULT: $ERRORS check(s) failed"
    exit 1
fi
echo "RESULT: All checks passed"
exit 0
