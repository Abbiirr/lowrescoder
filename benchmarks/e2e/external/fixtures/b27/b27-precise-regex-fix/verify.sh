#!/usr/bin/env bash
# Grading script for b27-precise-regex-fix
set -euo pipefail

ERRORS=0

# Check 1: All tests pass
if python -m pytest test_validator.py -q 2>&1 | grep -q "passed"; then
    echo "PASS: All validator tests pass"
else
    echo "FAIL: Some validator tests fail"
    ERRORS=$((ERRORS + 1))
fi

# Check 2: Only the regex pattern changed
# Count non-regex lines changed
DIFF_OUTPUT=$(diff <(git show HEAD:validator.py 2>/dev/null || cat /dev/null) validator.py 2>/dev/null || true)
CHANGED_LINES=$(echo "$DIFF_OUTPUT" | grep -c '^[<>]' || true)
if [ "$CHANGED_LINES" -le 2 ]; then
    echo "PASS: Minimal change ($CHANGED_LINES diff lines)"
else
    echo "FAIL: Too many lines changed ($CHANGED_LINES), expected only regex pattern"
    ERRORS=$((ERRORS + 1))
fi

# Check 3: Regex still contains core email structure
if grep -qE "EMAIL_PATTERN.*=.*re\.compile" validator.py; then
    echo "PASS: EMAIL_PATTERN still uses re.compile"
else
    echo "FAIL: EMAIL_PATTERN structure changed"
    ERRORS=$((ERRORS + 1))
fi

# Check 4: test_validator.py was not modified
if diff <(git show HEAD:test_validator.py 2>/dev/null || true) test_validator.py > /dev/null 2>&1; then
    echo "PASS: test_validator.py unchanged"
else
    echo "FAIL: test_validator.py was modified"
    ERRORS=$((ERRORS + 1))
fi

# Check 5: Regex allows dots in local part (functional check)
RESULT=$(python -c "from validator import is_valid_email; print(is_valid_email('a.b@c.com'))" 2>/dev/null)
if [ "$RESULT" = "True" ]; then
    echo "PASS: Regex accepts dots in local part"
else
    echo "FAIL: Regex still rejects dots in local part"
    ERRORS=$((ERRORS + 1))
fi

if [ "$ERRORS" -gt 0 ]; then
    echo "RESULT: $ERRORS check(s) failed"
    exit 1
fi
echo "RESULT: All checks passed"
exit 0
