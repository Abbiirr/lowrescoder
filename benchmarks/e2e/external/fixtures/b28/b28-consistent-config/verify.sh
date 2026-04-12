#!/usr/bin/env bash
set -euo pipefail

ERRORS=0

# Check 1: merger.py exists
if [ ! -f "project/merger.py" ]; then
    echo "FAIL: project/merger.py not found"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: project/merger.py exists"
fi

# Check 2: All tests pass
cd project
TEST_OUTPUT=$(python -m pytest test_merger.py -v 2>&1) || true
FAILED=$(echo "$TEST_OUTPUT" | grep -c "FAILED" || true)
if [ "$FAILED" -gt 0 ]; then
    echo "FAIL: $FAILED test(s) failed"
    echo "$TEST_OUTPUT" | grep "FAILED"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: All tests pass"
fi
cd ..

# Check 3: Output matches expected
RESULT=$(cd project && python -c "
import json
from merger import merge_configs
paths = ['config_a.json', 'config_b.json', 'config_c.json']
result = merge_configs(paths)
with open('expected_merged.json') as f:
    expected = json.load(f)
print('OK' if result == expected else 'FAIL')
" 2>&1)
if [ "$RESULT" = "OK" ]; then
    echo "PASS: Output matches expected"
else
    echo "FAIL: Output does not match expected: $RESULT"
    ERRORS=$((ERRORS + 1))
fi

# Check 4: Order-independent (test 3 permutations)
RESULT=$(cd project && python -c "
import json
from merger import merge_configs
import itertools
paths = ['config_a.json', 'config_b.json', 'config_c.json']
outputs = set()
for perm in itertools.permutations(paths):
    result = merge_configs(list(perm))
    outputs.add(json.dumps(result, sort_keys=True))
print('OK' if len(outputs) == 1 else f'FAIL: {len(outputs)} different outputs')
" 2>&1)
if [ "$RESULT" = "OK" ]; then
    echo "PASS: Order-independent (all permutations identical)"
else
    echo "FAIL: Order-dependent: $RESULT"
    ERRORS=$((ERRORS + 1))
fi

# Check 5: Deep merge works (nested keys from all files present)
RESULT=$(cd project && python -c "
from merger import merge_configs
result = merge_configs(['config_a.json', 'config_b.json', 'config_c.json'])
db = result.get('database', {})
keys = set(db.keys())
required = {'host', 'port', 'name', 'pool_size', 'ssl'}
print('OK' if required.issubset(keys) else f'FAIL: missing {required - keys}')
" 2>&1)
if [ "$RESULT" = "OK" ]; then
    echo "PASS: Deep merge preserves all nested keys"
else
    echo "FAIL: Deep merge incomplete: $RESULT"
    ERRORS=$((ERRORS + 1))
fi

# Check 6: Conflict resolution correct
RESULT=$(cd project && python -c "
from merger import merge_configs
result = merge_configs(['config_a.json', 'config_b.json', 'config_c.json'])
v = result['app']['version']
print('OK' if v == '2.1.0' else f'FAIL: version={v}')
" 2>&1)
if [ "$RESULT" = "OK" ]; then
    echo "PASS: Conflict resolution correct"
else
    echo "FAIL: Conflict resolution wrong: $RESULT"
    ERRORS=$((ERRORS + 1))
fi

if [ "$ERRORS" -gt 0 ]; then
    echo "RESULT: $ERRORS check(s) failed"
    exit 1
fi
echo "RESULT: All checks passed"
exit 0
