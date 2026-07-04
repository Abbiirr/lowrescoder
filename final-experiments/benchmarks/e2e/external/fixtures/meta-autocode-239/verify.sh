#!/usr/bin/env bash
set -e
echo "=== TASK-239: get_default_branch Key Fix ==="
[ -f "src/branch_info.py" ] || { echo "FAIL: branch_info.py not found"; exit 1; }
python -m pytest tests/test_branch_info.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: get_default_branch() reads 'default_branch'." || echo "FAIL"
exit $TEST_EXIT
