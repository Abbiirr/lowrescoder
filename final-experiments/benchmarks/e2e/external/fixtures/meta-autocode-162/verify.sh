#!/usr/bin/env bash
set -e
echo "=== TASK-162: Digit Sum Negative Number Fix ==="
[ -f "src/number_utils.py" ] || { echo "FAIL: number_utils.py not found"; exit 1; }
python -m pytest tests/test_number_utils.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: digit_sum() handles negative numbers." || echo "FAIL"
exit $TEST_EXIT
