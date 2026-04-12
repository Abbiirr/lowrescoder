#!/usr/bin/env bash
set -euo pipefail

ERRORS=0

# Check 1: pipeline.py exists
if [ ! -f "project/pipeline.py" ]; then
    echo "FAIL: project/pipeline.py not found"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: project/pipeline.py exists"
fi

# Check 2: All tests pass
cd project
TEST_OUTPUT=$(python -m pytest test_pipeline.py -v 2>&1) || true
FAILED=$(echo "$TEST_OUTPUT" | grep -c "FAILED" || true)
if [ "$FAILED" -gt 0 ]; then
    echo "FAIL: $FAILED test(s) failed"
    echo "$TEST_OUTPUT" | grep "FAILED"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: All tests pass"
fi
cd ..

# Check 3: Pipeline produces output
cd project
python pipeline.py input.csv output.json 2>&1 || true
cd ..
if [ -f "project/output.json" ]; then
    echo "PASS: output.json produced"
else
    echo "FAIL: output.json not produced"
    ERRORS=$((ERRORS + 1))
fi

# Check 4: Output matches expected
if [ -f "project/output.json" ] && [ -f "project/expected_output.json" ]; then
    MATCH=$(cd project && python -c "
import json
with open('output.json') as f: out = json.load(f)
with open('expected_output.json') as f: exp = json.load(f)
print('OK' if out == exp else 'FAIL')
" 2>&1)
    if [ "$MATCH" = "OK" ]; then
        echo "PASS: Output matches expected"
    else
        echo "FAIL: Output does not match expected"
        ERRORS=$((ERRORS + 1))
    fi
fi

# Check 5: Correct record count
if [ -f "project/output.json" ]; then
    COUNT=$(cd project && python -c "
import json
with open('output.json') as f: data = json.load(f)
print(len(data))
" 2>&1)
    if [ "$COUNT" = "5" ]; then
        echo "PASS: Correct record count (5)"
    else
        echo "FAIL: Wrong record count: $COUNT (expected 5)"
        ERRORS=$((ERRORS + 1))
    fi
fi

# Check 6: Sorted by salary descending
if [ -f "project/output.json" ]; then
    SORTED=$(cd project && python -c "
import json
with open('output.json') as f: data = json.load(f)
salaries = [r['salary'] for r in data]
print('OK' if salaries == sorted(salaries, reverse=True) else 'FAIL')
" 2>&1)
    if [ "$SORTED" = "OK" ]; then
        echo "PASS: Sorted by salary descending"
    else
        echo "FAIL: Not sorted correctly"
        ERRORS=$((ERRORS + 1))
    fi
fi

if [ "$ERRORS" -gt 0 ]; then
    echo "RESULT: $ERRORS check(s) failed"
    exit 1
fi
echo "RESULT: All checks passed"
exit 0
