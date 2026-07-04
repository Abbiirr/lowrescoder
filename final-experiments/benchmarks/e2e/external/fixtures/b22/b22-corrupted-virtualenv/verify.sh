#!/usr/bin/env bash
set -euo pipefail

ERRORS=0

# Check 1: Virtualenv exists
if [ -d venv ] && [ -f venv/bin/activate ]; then
    echo "PASS: Virtualenv directory exists with activate script"
else
    echo "FAIL: Virtualenv directory or activate script missing"
    ERRORS=$((ERRORS + 1))
fi

# Check 2: Python interpreter works
if venv/bin/python -c "print('ok')" > /dev/null 2>&1; then
    echo "PASS: Virtualenv Python interpreter works"
else
    echo "FAIL: Virtualenv Python interpreter broken"
    ERRORS=$((ERRORS + 1))
fi

# Check 3: pip --version works
if venv/bin/pip --version > /dev/null 2>&1; then
    echo "PASS: pip --version works"
else
    echo "FAIL: pip --version fails"
    ERRORS=$((ERRORS + 1))
fi

# Check 4: pip can resolve packages
if venv/bin/pip install --dry-run requests > /dev/null 2>&1; then
    echo "PASS: pip can resolve packages (dry-run install requests)"
else
    echo "FAIL: pip cannot resolve packages"
    ERRORS=$((ERRORS + 1))
fi

# Check 5: Activate script works (source in a subshell)
if bash -c "source venv/bin/activate && which python | grep -q venv" 2>/dev/null; then
    echo "PASS: Virtualenv activates cleanly"
else
    echo "FAIL: Virtualenv activation failed"
    ERRORS=$((ERRORS + 1))
fi

if [ "$ERRORS" -gt 0 ]; then
    echo "RESULT: $ERRORS check(s) failed"
    exit 1
fi
echo "RESULT: All checks passed"
exit 0
