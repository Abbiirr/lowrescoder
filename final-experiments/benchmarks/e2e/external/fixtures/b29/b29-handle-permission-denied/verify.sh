#!/usr/bin/env bash
# Grading script for b29-handle-permission-denied
set -euo pipefail

ERRORS=0

# Ensure test files exist
echo "readable content" > allowed.txt
echo "secret" > denied.txt
chmod 000 denied.txt

# Check 1: Script doesn't crash
if python -c "from file_reader import read_all; read_all(['allowed.txt', 'denied.txt'])" 2>/dev/null; then
    echo "PASS: Script does not crash on permission denied"
else
    echo "FAIL: Script crashes on permission denied"
    ERRORS=$((ERRORS + 1))
fi

# Check 2: Readable files are processed
RESULT=$(python -c "
from file_reader import read_all
r = read_all(['allowed.txt', 'denied.txt'])
if isinstance(r, tuple):
    results, errors = r
else:
    results = r
paths = [x['path'] for x in results]
print('allowed.txt' in paths)
" 2>/dev/null || echo "False")
if echo "$RESULT" | grep -q "True"; then
    echo "PASS: Readable files processed correctly"
else
    echo "FAIL: Readable files not processed"
    ERRORS=$((ERRORS + 1))
fi

# Check 3: Failed files reported
REPORTED=$(python -c "
from file_reader import read_all
r = read_all(['allowed.txt', 'denied.txt'])
if isinstance(r, tuple):
    results, errors = r
    print(len(errors) > 0)
else:
    # Check that denied.txt is not in results (was skipped)
    paths = [x['path'] for x in r]
    print('denied.txt' not in paths)
" 2>/dev/null || echo "False")
if echo "$REPORTED" | grep -q "True"; then
    echo "PASS: Failed files reported or skipped"
else
    echo "FAIL: Failed files not reported"
    ERRORS=$((ERRORS + 1))
fi

# Check 4: All tests pass
# Restore permissions for test cleanup
chmod 644 denied.txt 2>/dev/null || true
rm -f allowed.txt denied.txt
if python -m pytest test_reader.py -q 2>&1 | grep -q "passed"; then
    echo "PASS: All tests pass"
else
    echo "FAIL: Some tests fail"
    python -m pytest test_reader.py -q 2>&1 | tail -5
    ERRORS=$((ERRORS + 1))
fi

# Check 5: Error handling code exists
if grep -qE '(try|except|PermissionError)' file_reader.py; then
    echo "PASS: Permission error handling found"
else
    echo "FAIL: No permission error handling found"
    ERRORS=$((ERRORS + 1))
fi

# Check 6: test_reader.py was not modified
if diff <(git show HEAD:test_reader.py 2>/dev/null || true) test_reader.py > /dev/null 2>&1; then
    echo "PASS: test_reader.py unchanged"
else
    echo "FAIL: test_reader.py was modified"
    ERRORS=$((ERRORS + 1))
fi

# Cleanup
chmod 644 denied.txt 2>/dev/null || true
rm -f allowed.txt denied.txt

if [ "$ERRORS" -gt 0 ]; then
    echo "RESULT: $ERRORS check(s) failed"
    exit 1
fi
echo "RESULT: All checks passed"
exit 0
