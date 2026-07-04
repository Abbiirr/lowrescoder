#!/usr/bin/env bash
set -e
echo "=== TASK-071: axios Non-2xx Error Response Detection Fix ==="
[ -f "src/error_detector.py" ] || { echo "FAIL: error_detector.py not found"; exit 1; }
python -m pytest tests/test_error_detector.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: is_error_response() catches all non-2xx codes." || echo "FAIL"
exit $TEST_EXIT
