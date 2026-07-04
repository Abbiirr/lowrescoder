#!/usr/bin/env bash
# Grading script for b17-split-test-file
set -euo pipefail

ERRORS=0

# Check 1: Per-module test files exist
for f in test_calculator.py test_formatter.py test_validator.py; do
    if [ -f "$f" ]; then
        echo "PASS: $f exists"
    else
        echo "FAIL: $f does not exist"
        ERRORS=$((ERRORS + 1))
    fi
done

# Check 2: test_all.py no longer has test content (or is removed)
if [ -f test_all.py ]; then
    TEST_CLASSES=$(grep -c 'class Test' test_all.py 2>/dev/null || true)
    TEST_CLASSES=${TEST_CLASSES:-0}
    TEST_DEFS=$(grep -c 'def test_' test_all.py 2>/dev/null || true)
    TEST_DEFS=${TEST_DEFS:-0}
    if [ "$TEST_CLASSES" -gt 0 ] || [ "$TEST_DEFS" -gt 0 ]; then
        echo "FAIL: test_all.py still contains test code ($TEST_CLASSES classes, $TEST_DEFS test functions)"
        ERRORS=$((ERRORS + 1))
    else
        echo "PASS: test_all.py no longer contains tests"
    fi
else
    echo "PASS: test_all.py removed"
fi

# Check 3: test_calculator.py contains calculator tests
if [ -f test_calculator.py ]; then
    if grep -q 'Calculator' test_calculator.py && grep -q 'def test_' test_calculator.py; then
        echo "PASS: test_calculator.py has Calculator tests"
    else
        echo "FAIL: test_calculator.py missing Calculator tests"
        ERRORS=$((ERRORS + 1))
    fi
fi

# Check 4: test_formatter.py contains formatter tests
if [ -f test_formatter.py ]; then
    if grep -q 'format_' test_formatter.py && grep -q 'def test_' test_formatter.py; then
        echo "PASS: test_formatter.py has formatter tests"
    else
        echo "FAIL: test_formatter.py missing formatter tests"
        ERRORS=$((ERRORS + 1))
    fi
fi

# Check 5: test_validator.py contains validator tests
if [ -f test_validator.py ]; then
    if grep -q 'validate_' test_validator.py && grep -q 'def test_' test_validator.py; then
        echo "PASS: test_validator.py has validator tests"
    else
        echo "FAIL: test_validator.py missing validator tests"
        ERRORS=$((ERRORS + 1))
    fi
fi

# Check 6: All tests pass across all new test files
TOTAL_TESTS=0
for f in test_calculator.py test_formatter.py test_validator.py; do
    if [ -f "$f" ]; then
        if python -m pytest "$f" -v > "test_output_${f%.py}.log" 2>&1; then
            COUNT=$(grep -c 'PASSED' "test_output_${f%.py}.log" || echo 0)
            TOTAL_TESTS=$((TOTAL_TESTS + COUNT))
            echo "PASS: $f — all tests pass ($COUNT passed)"
        else
            echo "FAIL: $f — tests fail"
            tail -20 "test_output_${f%.py}.log"
            ERRORS=$((ERRORS + 1))
        fi
    fi
done

# Check 7: No tests were lost (original had specific test count)
# Count the original expected tests
ORIGINAL_TEST_COUNT=34  # From the original test_all.py

if [ "$TOTAL_TESTS" -ge "$ORIGINAL_TEST_COUNT" ]; then
    echo "PASS: No tests lost ($TOTAL_TESTS tests, expected >= $ORIGINAL_TEST_COUNT)"
else
    echo "FAIL: Tests may have been lost ($TOTAL_TESTS tests, expected >= $ORIGINAL_TEST_COUNT)"
    ERRORS=$((ERRORS + 1))
fi

# Result
if [ "$ERRORS" -gt 0 ]; then
    echo "RESULT: $ERRORS check(s) failed"
    exit 1
fi

echo "RESULT: All checks passed"
exit 0
