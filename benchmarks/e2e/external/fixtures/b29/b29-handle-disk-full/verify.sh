#!/usr/bin/env bash
# Grading script for b29-handle-disk-full
set -euo pipefail

ERRORS=0

# Check 1: All tests pass
if python -m pytest test_writer.py -q 2>&1 | grep -q "passed"; then
    echo "PASS: All tests pass"
else
    echo "FAIL: Some tests fail"
    python -m pytest test_writer.py -q 2>&1 | tail -5
    ERRORS=$((ERRORS + 1))
fi

# Check 2: Normal write still works
python -c "
from writer import write_report
import json, os
write_report('verify_test.json', {'a': 1})
with open('verify_test.json') as f:
    assert json.load(f) == {'a': 1}
os.remove('verify_test.json')
print('ok')
" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "PASS: Normal write still works"
else
    echo "FAIL: Normal write broken"
    ERRORS=$((ERRORS + 1))
fi

# Check 3: Error handling code exists
if grep -qE '(try|except|OSError)' writer.py; then
    echo "PASS: Error handling code found in writer.py"
else
    echo "FAIL: No error handling found in writer.py"
    ERRORS=$((ERRORS + 1))
fi

# Check 4: Cleanup logic exists (os.remove or os.unlink or Path.unlink)
if grep -qE '(os\.remove|os\.unlink|unlink|cleanup)' writer.py; then
    echo "PASS: Cleanup logic found in writer.py"
else
    echo "FAIL: No cleanup logic found in writer.py"
    ERRORS=$((ERRORS + 1))
fi

# Check 5: test_writer.py was not modified
if diff <(git show HEAD:test_writer.py 2>/dev/null || true) test_writer.py > /dev/null 2>&1; then
    echo "PASS: test_writer.py unchanged"
else
    echo "FAIL: test_writer.py was modified"
    ERRORS=$((ERRORS + 1))
fi

if [ "$ERRORS" -gt 0 ]; then
    echo "RESULT: $ERRORS check(s) failed"
    exit 1
fi
echo "RESULT: All checks passed"
exit 0
