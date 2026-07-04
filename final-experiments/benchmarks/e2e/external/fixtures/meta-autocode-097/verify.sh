#!/usr/bin/env bash
set -e
echo "=== TASK-097: axios Retry Backoff Multiplication Fix ==="
[ -f "src/retry_calculator.py" ] || { echo "FAIL: retry_calculator.py not found"; exit 1; }
python -m pytest tests/test_retry_calculator.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: get_retry_delay() uses multiplication for exponential backoff." || echo "FAIL"
exit $TEST_EXIT
