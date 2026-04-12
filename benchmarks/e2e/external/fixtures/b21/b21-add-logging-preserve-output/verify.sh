#!/usr/bin/env bash
set -euo pipefail

ERRORS=0

# Capture original expected output (re-derive from known input)
EXPECTED_STDOUT="NAME	SCORE	STATUS
Alice	95	PASS
Bob	82	PASS
Charlie	67	PASS
Diana	91	PASS
Eve	55	FAIL
---
Total: 5 students
Passing: 4/5"

# Check 1: stdout output is unchanged
ACTUAL_STDOUT=$(python pipeline.py input.csv 2>/dev/null)

if [ "$ACTUAL_STDOUT" = "$EXPECTED_STDOUT" ]; then
    echo "PASS: stdout output is byte-for-byte identical"
else
    echo "FAIL: stdout output changed"
    echo "--- EXPECTED ---"
    echo "$EXPECTED_STDOUT"
    echo "--- ACTUAL ---"
    echo "$ACTUAL_STDOUT"
    ERRORS=$((ERRORS + 1))
fi

# Check 2: All 4 original tests pass
TEST_RESULT=$(python -m pytest test_pipeline.py -v 2>&1)
PASSED=$(echo "$TEST_RESULT" | grep -c " PASSED" || true)

if [ "$PASSED" -ge 4 ]; then
    echo "PASS: All 4 original tests pass"
else
    echo "FAIL: Tests broken ($PASSED/4 passed)"
    echo "$TEST_RESULT"
    ERRORS=$((ERRORS + 1))
fi

# Check 3: Logging messages appear in stderr or log file
STDERR_OUTPUT=$(python pipeline.py input.csv 2>&1 1>/dev/null)
LOG_FILE_EXISTS=false
if [ -f "pipeline.log" ]; then
    LOG_FILE_EXISTS=true
    LOG_CONTENT=$(cat pipeline.log)
fi

HAS_LOGGING=false
if echo "$STDERR_OUTPUT" | grep -qi "process\|start\|complete\|record\|log"; then
    HAS_LOGGING=true
fi
if [ "$LOG_FILE_EXISTS" = true ] && echo "$LOG_CONTENT" | grep -qi "process\|start\|complete\|record\|log"; then
    HAS_LOGGING=true
fi

if [ "$HAS_LOGGING" = true ]; then
    echo "PASS: Logging messages found"
else
    echo "FAIL: No logging messages in stderr or pipeline.log"
    ERRORS=$((ERRORS + 1))
fi

# Check 4: Uses Python logging module
if grep -q "import logging\|from logging" pipeline.py; then
    echo "PASS: Uses Python logging module"
else
    echo "FAIL: Does not use Python logging module"
    ERRORS=$((ERRORS + 1))
fi

if [ "$ERRORS" -gt 0 ]; then
    echo "RESULT: $ERRORS check(s) failed"
    exit 1
fi
echo "RESULT: All checks passed"
exit 0
