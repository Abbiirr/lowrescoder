#!/usr/bin/env bash
set -e
echo "=== TASK-247: get_response_data Wrong Key Fix ==="
[ -f "src/response_data.py" ] || { echo "FAIL: response_data.py not found"; exit 1; }
python -m pytest tests/test_response_data.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: get_response_data() reads 'data' key." || echo "FAIL"
exit $TEST_EXIT
