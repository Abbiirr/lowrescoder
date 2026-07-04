#!/usr/bin/env bash
set -e
echo "=== TASK-240: format_response_time Divisor Fix ==="
[ -f "src/response_time.py" ] || { echo "FAIL: response_time.py not found"; exit 1; }
python -m pytest tests/test_response_time.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: format_response_time() divides by 1000." || echo "FAIL"
exit $TEST_EXIT
