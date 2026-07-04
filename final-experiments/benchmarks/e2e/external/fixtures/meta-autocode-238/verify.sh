#!/usr/bin/env bash
set -e
echo "=== TASK-238: is_timeout_error Key Fix ==="
[ -f "src/error_classifier.py" ] || { echo "FAIL: error_classifier.py not found"; exit 1; }
python -m pytest tests/test_error_classifier.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: is_timeout_error() checks 'code'." || echo "FAIL"
exit $TEST_EXIT
