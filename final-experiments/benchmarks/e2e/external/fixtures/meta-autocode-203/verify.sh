#!/usr/bin/env bash
set -e
echo "=== TASK-203: Fork Permission Fix ==="
[ -f "src/fork_checker.py" ] || { echo "FAIL: fork_checker.py not found"; exit 1; }
python -m pytest tests/test_fork_checker.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: can_fork() allows read, write, and admin permissions." || echo "FAIL"
exit $TEST_EXIT
