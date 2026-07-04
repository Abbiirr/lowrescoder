#!/usr/bin/env bash
set -e
echo "=== TASK-184: HTTP Success Check Fix ==="
[ -f "src/response_checker.py" ] || { echo "FAIL: response_checker.py not found"; exit 1; }
python -m pytest tests/test_response_checker.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: is_success() accepts any 2xx status code." || echo "FAIL"
exit $TEST_EXIT
