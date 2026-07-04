#!/usr/bin/env bash
set -euo pipefail

ERRORS=0

# Check 1: hasher.py exists
if [ ! -f "project/hasher.py" ]; then
    echo "FAIL: project/hasher.py not found"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: project/hasher.py exists"
fi

# Check 2: All tests pass
cd project
TEST_OUTPUT=$(python -m pytest test_hasher.py -v 2>&1) || true
FAILED=$(echo "$TEST_OUTPUT" | grep -c "FAILED" || true)
if [ "$FAILED" -gt 0 ]; then
    echo "FAIL: $FAILED test(s) failed"
    echo "$TEST_OUTPUT" | grep "FAILED"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: All tests pass"
fi
cd ..

# Check 3: All hashes match expected
RESULT=$(cd project && python -c "
import json
from hasher import hash_directory
result = hash_directory('test_files')
with open('expected_hashes.json') as f:
    expected = json.load(f)
print('OK' if result == expected else 'FAIL')
" 2>&1)
if [ "$RESULT" = "OK" ]; then
    echo "PASS: All hashes match expected values"
else
    echo "FAIL: Hashes do not match expected: $RESULT"
    ERRORS=$((ERRORS + 1))
fi

# Check 4: Reproducible across 3 runs
RESULT=$(cd project && python -c "
import json
from hasher import hash_directory
outputs = set()
for _ in range(3):
    result = hash_directory('test_files')
    outputs.add(json.dumps(result, sort_keys=True))
print('OK' if len(outputs) == 1 else 'FAIL')
" 2>&1)
if [ "$RESULT" = "OK" ]; then
    echo "PASS: Hashes reproducible across 3 runs"
else
    echo "FAIL: Non-reproducible hashes: $RESULT"
    ERRORS=$((ERRORS + 1))
fi

# Check 5: hash_file returns 64-char hex string
RESULT=$(cd project && python -c "
from hasher import hash_file
h = hash_file('test_files/hello.txt')
print('OK' if isinstance(h, str) and len(h) == 64 else 'FAIL')
" 2>&1)
if [ "$RESULT" = "OK" ]; then
    echo "PASS: hash_file returns proper SHA-256 hex digest"
else
    echo "FAIL: hash_file return format wrong: $RESULT"
    ERRORS=$((ERRORS + 1))
fi

if [ "$ERRORS" -gt 0 ]; then
    echo "RESULT: $ERRORS check(s) failed"
    exit 1
fi
echo "RESULT: All checks passed"
exit 0
