#!/usr/bin/env bash
# Grading script for b27-minimal-config-change
set -euo pipefail

ERRORS=0

# Check 1: Tests pass
if python -m pytest test_app.py -q 2>&1 | grep -q "passed"; then
    echo "PASS: All tests pass"
else
    echo "FAIL: Tests do not pass"
    ERRORS=$((ERRORS + 1))
fi

# Check 2: config.yaml has port 8080
if grep -q 'port: 8080' config.yaml; then
    echo "PASS: config.yaml has correct port 8080"
else
    echo "FAIL: config.yaml does not have port 8080"
    ERRORS=$((ERRORS + 1))
fi

# Check 3: Only config.yaml was changed
APP_CHANGED=false
TEST_CHANGED=false
if ! diff <(git show HEAD:app.py 2>/dev/null || true) app.py > /dev/null 2>&1; then
    APP_CHANGED=true
fi
if ! diff <(git show HEAD:test_app.py 2>/dev/null || true) test_app.py > /dev/null 2>&1; then
    TEST_CHANGED=true
fi

if [ "$APP_CHANGED" = false ] && [ "$TEST_CHANGED" = false ]; then
    echo "PASS: Only config.yaml modified"
else
    echo "FAIL: app.py or test_app.py was modified"
    ERRORS=$((ERRORS + 1))
fi

# Check 4: Minimal diff in config.yaml
CHANGED_LINES=$(diff <(git show HEAD:config.yaml 2>/dev/null || echo "port: 9090") config.yaml 2>/dev/null | grep -c '^[<>]' || true)
if [ "$CHANGED_LINES" -le 2 ]; then
    echo "PASS: Minimal config change ($CHANGED_LINES diff lines)"
else
    echo "FAIL: Too many changes in config.yaml ($CHANGED_LINES diff lines)"
    ERRORS=$((ERRORS + 1))
fi

if [ "$ERRORS" -gt 0 ]; then
    echo "RESULT: $ERRORS check(s) failed"
    exit 1
fi
echo "RESULT: All checks passed"
exit 0
