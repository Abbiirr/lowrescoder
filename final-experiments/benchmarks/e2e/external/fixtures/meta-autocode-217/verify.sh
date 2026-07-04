#!/usr/bin/env bash
set -e
echo "=== TASK-217: is_detached_head Key Fix ==="
[ -f "src/head_checker.py" ] || { echo "FAIL: head_checker.py not found"; exit 1; }
python -m pytest tests/test_head_checker.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: is_detached_head() reads correct key." || echo "FAIL"
exit $TEST_EXIT
