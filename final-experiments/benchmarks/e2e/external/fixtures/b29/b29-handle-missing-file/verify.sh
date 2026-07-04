#!/usr/bin/env bash
# Grading script for b29-handle-missing-file
set -euo pipefail

ERRORS=0

# Clean state: ensure config.json does not exist
rm -f config.json

# Check 1: App doesn't crash when config.json is missing
if python -c "from app import load_config; load_config()" 2>/dev/null; then
    echo "PASS: App does not crash when config.json is missing"
else
    echo "FAIL: App crashes when config.json is missing"
    ERRORS=$((ERRORS + 1))
fi

# Check 2: Default config created
rm -f config.json
python -c "from app import load_config; load_config()" 2>/dev/null
if [ -f config.json ]; then
    echo "PASS: Default config.json was created"
else
    echo "FAIL: config.json was not created"
    ERRORS=$((ERRORS + 1))
fi

# Check 3: Default config has required keys
if python -c "
import json
with open('config.json') as f:
    c = json.load(f)
assert c['port'] == 8080
assert c['debug'] == False
print('ok')
" 2>/dev/null | grep -q "ok"; then
    echo "PASS: Default config has correct values"
else
    echo "FAIL: Default config missing port=8080 or debug=false"
    ERRORS=$((ERRORS + 1))
fi

# Check 4: All tests pass
rm -f config.json
if python -m pytest test_app.py -q 2>&1 | grep -q "passed"; then
    echo "PASS: All tests pass"
else
    echo "FAIL: Some tests fail"
    ERRORS=$((ERRORS + 1))
fi

# Check 5: test_app.py was not modified
if diff <(git show HEAD:test_app.py 2>/dev/null || true) test_app.py > /dev/null 2>&1; then
    echo "PASS: test_app.py unchanged"
else
    echo "FAIL: test_app.py was modified"
    ERRORS=$((ERRORS + 1))
fi

if [ "$ERRORS" -gt 0 ]; then
    echo "RESULT: $ERRORS check(s) failed"
    exit 1
fi
echo "RESULT: All checks passed"
exit 0
