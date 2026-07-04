#!/usr/bin/env bash
set -e
echo "=== TASK-064: lazygit Commit Message Length Threshold Fix ==="
[ -f "src/commit_checker.py" ] || { echo "FAIL: commit_checker.py not found"; exit 1; }
python -m pytest tests/test_commit_checker.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: check_commit_message() warns for > 50 char subjects." || echo "FAIL"
exit $TEST_EXIT
