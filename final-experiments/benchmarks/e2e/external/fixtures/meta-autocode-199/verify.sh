#!/usr/bin/env bash
set -e
echo "=== TASK-199: Conventional Commit Type Fix ==="
[ -f "src/commit_checker.py" ] || { echo "FAIL: commit_checker.py not found"; exit 1; }
python -m pytest tests/test_commit_checker.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: is_conventional_commit() handles mixed-case types." || echo "FAIL"
exit $TEST_EXIT
