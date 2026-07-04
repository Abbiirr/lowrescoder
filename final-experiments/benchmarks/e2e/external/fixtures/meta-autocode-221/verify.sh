#!/usr/bin/env bash
set -e
echo "=== TASK-221: is_repo_archived Key Fix ==="
[ -f "src/repo_checker.py" ] || { echo "FAIL: repo_checker.py not found"; exit 1; }
python -m pytest tests/test_repo_checker.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: is_repo_archived() reads correct key." || echo "FAIL"
exit $TEST_EXIT
