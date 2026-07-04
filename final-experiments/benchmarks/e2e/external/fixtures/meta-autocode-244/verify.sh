#!/usr/bin/env bash
set -e
echo "=== TASK-244: is_branch_merged Wrong Key Fix ==="
[ -f "src/branch_merged.py" ] || { echo "FAIL: branch_merged.py not found"; exit 1; }
python -m pytest tests/test_branch_merged.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: is_branch_merged() reads 'merged' key." || echo "FAIL"
exit $TEST_EXIT
