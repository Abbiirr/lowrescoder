#!/usr/bin/env bash
set -e
echo "=== TASK-087: gitea Branch Name Double-Dot Validation Fix ==="
[ -f "src/branch_checker.py" ] || { echo "FAIL: branch_checker.py not found"; exit 1; }
python -m pytest tests/test_branch_checker.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: is_valid_branch_name() rejects double-dot." || echo "FAIL"
exit $TEST_EXIT
