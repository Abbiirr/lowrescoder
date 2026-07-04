#!/usr/bin/env bash
set -e
echo "=== TASK-246: get_rate_limit Wrong Key Fix ==="
[ -f "src/rate_limit.py" ] || { echo "FAIL: rate_limit.py not found"; exit 1; }
python -m pytest tests/test_rate_limit.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: get_rate_limit() reads 'limit' key." || echo "FAIL"
exit $TEST_EXIT
