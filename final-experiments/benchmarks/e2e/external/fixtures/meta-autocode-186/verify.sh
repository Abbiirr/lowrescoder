#!/usr/bin/env bash
set -e
echo "=== TASK-186: Response Threshold Strict Check Fix ==="
[ -f "src/threshold_check.py" ] || { echo "FAIL: threshold_check.py not found"; exit 1; }
python -m pytest tests/test_threshold_check.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: is_response_ok() uses strict less-than." || echo "FAIL"
exit $TEST_EXIT
